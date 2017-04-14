from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.list import ListView 
from django.views.generic import View
from django.forms import inlineformset_factory, formset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from decimal import Decimal
from .forms import ContractorClassForm
from .models import (CPLSubmissionBaseRate, ProfessionalSubmissionBaseRate, CPLSubmissionManualRate, ProfessionalSubmissionManualRate,
                     CPLSubmission, ProfessionalSubmission, SubmissionSet, ContractorClass, ProfessionalClass, Submission)
from .serializers import (ContractorClassSerializer, ProfessionalClassSerializer, CPLSubmissionBaseRateSerializer,
						  ProfessionalSubmissionBaseRateSerializer, CPLSubmissionManualRateSerializer, ProfessionalSubmissionManualRateSerializer,
						  CPLSubmissionSerializer, ProfessionalSubmissionSerializer, SubmissionSetSerializer, UserSerializer)
import json
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import logout
from django.contrib.auth.models import User
from rest_framework.decorators import api_view
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import APIException
from rest_framework import authentication, permissions
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework import viewsets
import rest_framework.serializers
import importlib
		
#Views go here.
class Index(View):    
    def get(self, request, *args, **manual_rate_data):
        contractor_classes = ContractorClass.objects.all()    
        context = {"contractor_classes" : contractor_classes}    
        return render(request, 'envirorater/home.html', context)
	
@api_view(['GET'])
def api_root(request, format=None):
    return Response({
		'users' : reverse('user-list', request=request, format=format),
        'submissions': reverse('submissionset-list', request=request, format=format),
        'contractors': reverse('contractors-list', request=request, format=format),
		'professionals': reverse('professionals-list', request=request, format=format)
    })

class UserViewSet(viewsets.ModelViewSet):
	
	queryset = User.objects.all()
	serializer_class = UserSerializer
	permission_classes = (permissions.AllowAny, )
	
class SubmissionViewSet(viewsets.ModelViewSet):

	queryset = SubmissionSet.objects.all().order_by('-id')
	serializer_class = SubmissionSetSerializer
	permission_classes = (permissions.AllowAny, )
	
	def create(self, request):

		raw = request.data.get('raw', False)		
		serializer = SubmissionSetSerializer(data = request.data)
		
		if serializer.is_valid():
			validated_data = serializer.validated_data
			submission_set = serializer.create(validated_data, owner = request.user,
											   context = {'request' : request})
			ret_subset = SubmissionSetSerializer(submission_set, context = {'request' : request})
			return Response(ret_subset.data)
		return Response(submission_set.error)
	
	def update(self, request, pk):
		
		submission_set = SubmissionSet.objects.get(id = pk)
		serializer = SubmissionSetSerializer(data = request.data)
		
		if serializer.is_valid():
			validated_data = serializer.validated_data
			serializer.update(submission_set, validated_data)
			
			
	
	def partial_update(self, request, pk):
		pass
# 	@list_route(methods=['get'])
# 	def units(self, request, pk=None):
# 		submission = SubmissionSet.objects.get(pk=pk)
		
class CoverageViewSet(viewsets.ViewSet):
	permission_classes = (permissions.AllowAny,)
	
	def cpl_details(self, request, *args, **kwargs):
		submission_set = SubmissionSet.objects.get(pk = kwargs['submission_set'])
		if submission_set.cpl_submission:
			serializer = CPLSubmissionSerializer(submission_set.cpl_submission,
												 context = {'request' : request})
			return Response(serializer.data)
		else:
			submission_set.cpl_submission = CPLSubmission.objects.create(submission_set = submission_set)
			serializer = CPLSubmissionSerializer(submission_set.cpl_submission,
												 context = {'request' : request})
			return Response(serializer.data)
			
	def pro_details(self, request, *args, **kwargs):
		submission_set = SubmissionSet.objects.get(pk = kwargs['submission_set'])
		if submission_set.professional_submission:
			serializer = ProfessionalSubmissionSerializer(submission_set.professional_submission,
														  context = {'request' : request})
			return Response(serializer.data)
		else:
			raise rest_framework.serializers.ValidationError('This Submission Set does not have a Professional Coverage Portion')
			
class BaseRatingUnitViewSet(viewsets.ViewSet):
	permission_classes = (permissions.AllowAny,)
	
	def setup(self, request, *args, **kwargs):
		submission_type_dict = {
			'cpl' : { 'attr' : 'cpl_submission', 'serializer' : CPLSubmissionSerializer},
			'pro' : { 'attr' : 'professional_submission', 'serializer' : ProfessionalSubmissionSerializer}
								}
		
		submission_type = kwargs['submission_type'].lower()
		submission_set = SubmissionSet.objects.get(pk = kwargs['submission_set'])
		settings_dict = submission_type_dict.pop(submission_type)		
		submission = getattr(submission_set, settings_dict['attr'])		
		serializer = settings_dict['serializer']
		
		return {
			'submission_set' : submission_set,
			'submission' : submission,
			'serializer' : serializer,
		}
	
	def list(self, request, *args, **kwargs):
		
		settings_dict = self.setup(request, *args, **kwargs)
		#Unpack the dict in to local variables for the function
		submission_set, submission, serializer = map(settings_dict.get, 
													 ('submission_set', 'submission', 'serializer')
													)
		
		if submission.base_rating_classes:
			serializer = serializer(submission.base_rating_classes, many = True,
														 context = {'request' : request})
			return Response(serializer.data)
		else:
			raise rest_framework.serializers.ValidationError('This CPL Submission does not have any base rating units yet.')
			
	
		
class ContractorClassViewSet(viewsets.ReadOnlyModelViewSet):
	"""
	This viewset automatically provides 'list' and 'detail' actions.
	"""
	queryset = ContractorClass.objects.all()
	serializer_class = ContractorClassSerializer
	lookup_field = 'iso_code'
	
		
class ProfessionalClassViewSet(viewsets.ReadOnlyModelViewSet):
		
	queryset = ProfessionalClass.objects.all()
	serializer_class = ProfessionalClassSerializer
	lookup_field = 'iso_code'

class PremiumModifierAPI(APIView):
	#I want a GET request with no arguments to return an options request
  	#detailing how to use the API
  	#Not sure how to do that yet so need to come back to this.
	permission_classes = (permissions.AllowAny,)
	
	from rest_framework.exceptions import ValidationError
	
	def get(self, request, *args, **kwargs):
		if request.query_params:
			query = PremiumModifierAPISerializer(request.query_params)
			premium = query.data['premium']
			factor_dict = {}
      #Once again limits are a special case.  We need the user to input them
      #'limit1/limit2';
			if query.data['modifier'] == 'limit':
				try:
					data_string = query.data['mod_value']
					limit1 = data_string.split('/')[0]
					limit2 = data_string.split('/')[1]
				except:
					raise rest_framework.serializers.ValidationError('Limits must be separated by a slash. Ex. 10000/5000')
				try:
					limit = Limit.objects.get(limit1__iexact = limit1, limit2__iexact = limit2)
					factor_dict = {'limit1' : limit2, 'limit2' : limit2}
				except ObjectDoesNotExist:
					raise rest_framework.serializers.ValidationError('That limit object could not be found')					
			else:
				factor_dict = {query.data['modifier'] : query.data['mod_value']}
			premium = SubmissionManualRate.mod_premium(premium, factor_dict)
			query._data['premium'] = premium
			return Response(query.data)
		else:
      #Note there has to be a better way to show an example
			raise rest_framework.serializers.ValidationError('Please make factor GET requests with premium, modifier, and mod_value arguments.')