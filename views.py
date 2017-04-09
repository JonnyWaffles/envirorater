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
                     CPLSubmission, ProfessionalSubmission, SubmissionSet)
from .serializers import (ContractorClassSerializer, ProfessionalClassSerializer)
import json
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import logout
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import APIException
from rest_framework import authentication, permissions
from rest_framework import status
from rest_framework.reverse import reverse
import rest_framework.serializers
import importlib
		
#Views go here.
class Index(View):    
    def get(self, request, *args, **manual_rate_data):
        contractor_classes = ContractorClass.objects.all()    
        context = {"contractor_classes" : contractor_classes}    
        return render(request, 'envirorater/home.html', context)

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