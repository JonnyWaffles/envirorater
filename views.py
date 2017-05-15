from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.list import ListView 
from django.views.generic import View
from django.forms import inlineformset_factory, formset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
#from django.urls import reverse
from decimal import Decimal
from .forms import ContractorClassForm
from .models import (CPLSubmissionBaseRate, ProfessionalSubmissionBaseRate, CPLSubmissionManualRate, ProfessionalSubmissionManualRate,
                     CPLSubmission, ProfessionalSubmission, SubmissionSet, ContractorClass, ProfessionalClass, Submission, ProfessionalRevenueBand,
                     Deductible, PriorActs, Aggregate, State, Nose, ContractorsPollutionRevenueBand, Limit)
from .serializers import (ContractorClassSerializer, ProfessionalClassSerializer, CPLSubmissionBaseRateSerializer,
						  ProfessionalSubmissionBaseRateSerializer, CPLSubmissionManualRateSerializer, ProfessionalSubmissionManualRateSerializer,
						  CPLSubmissionSerializer, ProfessionalSubmissionSerializer, SubmissionSetSerializer, UserSerializer,
                          PremiumModifierAPISerializer, ProfessionalRevenueBandSerializer, ContractorsPollutionRevenueBandSerializer, DeductibleSerializer,
                          PriorActsSerializer, AggregateSerializer, StateSerializer, NoseSerializer, LimitSerializer, CPLSubmissionManualRateSerializer)
import json
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import logout
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import (CreateAPIView, DestroyAPIView, GenericAPIView, ListAPIView, ListCreateAPIView,
                                     RetrieveAPIView, RetrieveDestroyAPIView, RetrieveUpdateAPIView, RetrieveUpdateDestroyAPIView, 
                                     UpdateAPIView)
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import APIException, ValidationError
from rest_framework import authentication, permissions
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework import viewsets
from rest_framework.serializers import ListSerializer
from rest_framework_bulk import BulkCreateModelMixin
import importlib
import collections


@api_view(['GET'])
@permission_classes(((permissions.AllowAny, )))
def api_root(request, format=None):

	response_dict = collections.OrderedDict()
	response_dict.update([
		('users', reverse('user-list', request=request, format=format)),
        ('submissions', reverse('submissions-list', request=request, format=format)),
        ('contractors', reverse('contractorclass-list', request=request, format=format)),
		('professionals', reverse('professionalclass-list', request=request, format=format)),
        ('factors', reverse('premium-modifier-api', request=request)),
		('pro_revenue_bands', reverse('professionalrevenueband-list', request=request, format=format)),
		('cpl_revenue_bands', reverse('contractorspollutionrevenueband-list', request=request, format=format)),
		('deductibles', reverse('deductible-list', request=request, format=format)),
		('prior_acts', reverse('prioracts-list', request=request, format=format)),
		('aggregates', reverse('aggregate-list', request=request, format=format)),
		('state', reverse('state-list', request=request, format=format)),
		('nose', reverse('nose-list', request=request, format=format)),
		('limit', reverse('limit-list', request=request, format=format))
	])

	return Response(response_dict)

class AdminOnlyViewMixin:

    permission_classes = (permissions.IsAdminUser, )


class UserViewSet(viewsets.ModelViewSet):

	queryset = User.objects.all()
	serializer_class = UserSerializer
	permission_classes = (permissions.AllowAny, )
	
class SubmissionSetViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	This is the primary entry point to the API. Submissions and all nested objects are created or updated here.

	create:
	Creates a new SubmissionSet containing either or both a cpl_submission and/or professional_submission.

	retrieve:
	Views a SubmissionSet based on ID. Example /envirorater/api/submissions/1 will retrieve the SubmissionSet 1 object.

	update:
	Updates a retrieved instance.

	destroy:
	Deletes a specified SubmissionSet by id.

	list:
	List all the SubmissionSets.
	"""	

	queryset = SubmissionSet.objects.all().order_by('-id')
	serializer_class = SubmissionSetSerializer
	permission_classes = (permissions.AllowAny, )

	def perform_create(self, serializer):
		
		user = self.request.user
		if user.is_anonymous:
			user = None
			
		raw = self.request.data.get('raw', False)
		
		
		if not isinstance(serializer, ListSerializer):
			serializer.save(owner = user, raw = raw)
		else:
			serializer.save(owner = user)

	def perform_update(self, serializer):			
		serializer.save()

class CPLSubmissionViewSet(viewsets.ModelViewSet):
	"""
	retrieve:
	Views this SubmissionSet's cpl_submission attribute based on SubmissionSet ID. Example /envirorater/api/submissions/1/cpl 
	retrieves SubmissionSet 1's CPLSubmission object.

	update:
	Updates a CPLSubmission instance.

	destroy:
	Deletes a specified SubmissionSet's CPLSubmission by SubmissionSet id.
	"""

	permission_classes = (permissions.AllowAny,)
	queryset = CPLSubmission.objects.all()

	serializer_class = CPLSubmissionSerializer

	def get_submission_set(self):
		submission_set = get_object_or_404(SubmissionSet, id = self.kwargs['submission_set'])
		return submission_set

	def get_object(self):
		submission_set = self.get_submission_set()
		return submission_set.cpl_submission

	def perform_update(self, serializer):
		serializer.save(submission_set = self.get_submission_set(), raw = self.request.data.get('raw', False))

class ProfessionalSubmissionViewSet(viewsets.ModelViewSet):
	"""	
	retrieve:
	Views this SubmissionSet's professional_submission attribute based on SubmissionSet ID. Example /envirorater/api/submissions/1/pro 
	retrieves SubmissionSet 1's ProfessionalSubmission object.

	update:
	Updates a specific ProfessionalSubmission instance.

	destroy:
	Deletes a specified SubmissionSet's ProfessionalSubmission by SubmissionSet id.
	"""

	permission_classes = (permissions.AllowAny,)
	queryset = ProfessionalSubmission.objects.all()

	serializer_class = ProfessionalSubmissionSerializer
	
	def get_submission_set(self):
		submission_set = get_object_or_404(SubmissionSet, id = self.kwargs['submission_set'])
		return submission_set

	def get_object(self):
		submission_set = self.get_submission_set()
		return submission_set.professional_submission

	def perform_update(self, serializer):
		serializer.save(submission_set = self.get_submission_set(), raw = self.request.data.get('raw', False))
		 
class CPLBaseRatingUnitViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	create:
	Creates a new CPLBaseRatingUnit on the specified SubmissionSet's CPLSubmission object.

	retrieve:
	View the specific base_rating_unit by iso_code. Example, /envirorater/api/submissions/1/cpl/units/94444
	would view the details of the submission's Aircraft refueling base rating unit if it existed. Each submission's
	base_rating_units must have a unique iso_code.

	update:
	Updates a specific CPLBaseRatingUnit.

	destroy:
	Deletes a specific CPLBaseRatingUnit from the CPLSubmission object.
	"""       

	permission_classes = (permissions.AllowAny,)

	queryset = CPLSubmissionBaseRate.objects.all()
	serializer_class = CPLSubmissionBaseRateSerializer
	lookup_field = 'iso_code'

	def get_queryset(self):
		submission_set = SubmissionSet.objects.get(pk = self.kwargs['submission_set'])
		return CPLSubmissionBaseRate.objects.filter(submission=submission_set.cpl_submission)

	def perform_create(self, serializer):
		submission_set = SubmissionSet.objects.get(pk = self.kwargs['submission_set'])
		serializer.save(submission = submission_set.cpl_submission, raw = self.request.data.get('raw', False))

	def perform_update(self, serializer):
		serializer.save(raw = self.request.data.get('raw', False))

class ProfessionalBaseRatingUnitViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Return the ProfessionalBaseRating Unit by iso_code.

	update:
	Update's the ProfessionalBaseRating Unit.

	patch:
	Partially update's the ProfessionalBaseRating Unit.

	destroy:
	Delete's the ProfessionalBaseRating Unit.

	list:
	Returns a list of all the ProfessionalSubmission's base_rating_units.
	"""    
	permission_classes = (permissions.AllowAny,)

	queryset = ProfessionalSubmissionBaseRate.objects.all()
	serializer_class = ProfessionalSubmissionBaseRateSerializer
	lookup_field = 'iso_code'

	def get_queryset(self):
		submission_set = SubmissionSet.objects.get(pk = self.kwargs['submission_set'])
		return ProfessionalSubmissionBaseRate.objects.filter(submission=submission_set.professional_submission)

	def perform_create(self, serializer):
		submission_set = SubmissionSet.objects.get(pk = self.kwargs['submission_set'])
		serializer.save(submission = submission_set.professional_submission, raw = self.request.data.get('raw', False))

	def perform_update(self, serializer):
		serializer.save(raw = self.request.data.get('raw', False))

class CPLSubmissionManualRateViewSet(viewsets.ModelViewSet):
	"""
	create:
	Creates the CPLSubmission's manual_rate attribute CPLManualRate object.
	
	retrieve:
	Return the CPLSubmission's manual_rate attribute's CPLManualRate object.
	
	update:
	Update's the CPLSubmission's manual_rate attribute's CPLManualRate object.
	
	patch:
	Partially update's the CPLSubmission's manual_rate attribute's CPLManualRate object. 
	
	destroy:
	Delete's the CPLSubmission's manual_rate attribute's CPLManualRate object.
	"""
	
	permission_classes = (permissions.AllowAny, )
	
	queryset = CPLSubmissionManualRate.objects.all()
	serializer_class = CPLSubmissionManualRateSerializer
	lookup_field = None
	
	def get_submission(self):
		submission_set = get_object_or_404(SubmissionSet, id = self.kwargs['submission_set'])
		
		assert hasattr(submission_set, 'cpl_submission'), (
			'SubmissionSet %s has no cpl_submission attribute. A CPLSubmission must exist before a'
			'CPLManualRate instance.' % (submission_set.id)
		)
		
		return submission_set.cpl_submission
	
	def get_queryset(self):
		cpl_submission = self.get_submission()
		return CPLSubmissionManualRate.objects.filter(submission = cpl_submission)
	
	def get_object(self):
		cpl_submission = self.get_submission()
		return CPLSubmissionManualRate.objects.get(submission = cpl_submission)
	
	def perform_create(self, serializer):
		cpl_submission = self.get_submission()
		serializer.save(submisson = cpl_submission)
		
class ProfessionalSubmissionManualRateViewSet(viewsets.ModelViewSet):
	"""
	create:
	Creates the ProfessionalSubmission's manual_rate attribute ProfessionalManualRate object.
	
	retrieve:
	Return the ProfessionalSubmission's manual_rate attribute's ProfessionalManualRate object.
	
	update:
	Update's the ProfessionalSubmission's manual_rate attribute's ProfessionalManualRate object.
	
	patch:
	Partially update's the ProfessionalSubmission's manual_rate attribute's ProfessionalManualRate object. 
	
	destroy:
	Delete's the ProfesisonalSubmission's manual_rate attribute's ProfessionalManualRate object.
	"""
	
	permission_classes = (permissions.AllowAny, )
	
	queryset = ProfessionalSubmissionManualRate.objects.all()
	serializer_class = ProfessionalSubmissionManualRateSerializer
	lookup_field = None
	
	def get_submission(self):
		submission_set = get_object_or_404(SubmissionSet, id = self.kwargs['submission_set'])
		
		assert hasattr(submission_set, 'professional_submission'), (
			'SubmissionSet %s has no professional_submission attribute. A ProfessionalSubmission must exist before a'
			'ProfessionalManualRate instance.' % (submission_set.id)
		)
		
		return submission_set.professional_submission
	
	def get_queryset(self):
		professional_submission = self.get_submission()
		return ProfessionalSubmissionManualRate.objects.filter(submission = professional_submission)
	
	def get_object(self):
		professional_submission = self.get_submission()
		return ProfessionalSubmissionManualRate.objects.get(submission = professional_submission)
	
	def perform_create(self, serializer):
		professional_submission = self.get_submission()
		serializer.save(submisson = professional_submission)	
		
class ContractorClassViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified ContractorClass by iso_code.

	update:
	Update's the ContractorClass *Admin Only in Production*.

	patch:
	Partially update's the ContractorClass *Admin Only in Production*.

	destroy:
	Delete's the ContractorClass *Admin Only in Production*.

	list:
	Returns a list of all ContractorClasses.
	"""

	permission_classes = (permissions.AllowAny,)

	queryset = ContractorClass.objects.all()
	serializer_class = ContractorClassSerializer
	lookup_field = 'iso_code'
    
class ProfessionalClassViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified ProfessionalClass by iso_code. Only superusers can see factors.

	update:
	Update's the ProfessionalClass *Admin Only in Production*.

	patch:
	Partially update's the ProfessionalClass *Admin Only in Production*.

	destroy:
	Delete's the ProfessionalClass *Admin Only in Production*.

	list:
	Returns a list of all ProfessionalClasses.
	"""

	permission_classes = (permissions.AllowAny,)

	queryset = ProfessionalClass.objects.all()
	serializer_class = ProfessionalClassSerializer
	lookup_field = 'iso_code'

class ProfessionalRevenueBandViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified ProfessionalRevenueBand by id. Only superusers can see factors.

	list:
	Returns a list of all ProfessionalRevenueBands. Only superusers can see factors.
	"""

	queryset = ProfessionalRevenueBand.objects.all()
	serializer_class = ProfessionalRevenueBandSerializer

class ContractorsPollutionRevenueBandViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified ContractorsPollutionRevenueBand by id. Only superusers can see factors.

	list:
	Returns a list of all ContractorsPollutionRevenueBands. Only superusers can see factors.
	"""

	queryset = ContractorsPollutionRevenueBand.objects.all()
	serializer_class = ContractorsPollutionRevenueBandSerializer

class DeductibleViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified Deductible by id. Only superusers can see factors.

	list:
	Returns a list of all Deductible. Only superusers can see factors.
	"""

	queryset = Deductible.objects.all()
	serializer_class = DeductibleSerializer

class LimitViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified Limit by id. Only superusers can see factors.

	list:
	Returns a list of all Limits. Only superusers can see factors.
	"""
	
	queryset = Limit.objects.all()
	serializer_class = LimitSerializer

class PriorActsViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified PriorActs by id. Only superusers can see factors.

	list:
	Returns a list of all PriorActs. Only superusers can see factors.
	"""

	queryset = PriorActs.objects.all()
	serializer_class = PriorActsSerializer

class AggregateViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified Aggregate by id. Only superusers can see factors.

	list:
	Returns a list of all Aggregates. Only superusers can see factors.
	"""

	queryset = Aggregate.objects.all()
	serializer_class = AggregateSerializer

class StateViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified State by id. Only superusers can see factors.

	list:
	Returns a list of all States. Only superusers can see factors.
	"""

	queryset = State.objects.all()
	serializer_class = StateSerializer

class NoseViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):
	"""
	retrieve:
	Returns the specified Nose by id. Only superusers can see factors.

	list:
	Returns a list of all Noses. Only superusers can see factors.
	"""

	queryset = Nose.objects.all()
	serializer_class = NoseSerializer

class PremiumModifierAPI(APIView):
    """
    get:
    Returns an empty PremiumModifierAPISerializer as an example.

    post:
    Takes a premium and one or more modifiers, returns the modified premium.
    Acceptable modifier values are 'limit', 'deductible', 'primary_nose_coverage',
    'mold_nose_coverage','aggregate_deductible_multiplier', or 'prior_acts_years'.
    """    
    permission_classes = (permissions.AllowAny,)
    
    def get(self, request, *args, **kwargs):
        print(reverse('premium-modifier-api', request=request))
        return Response(PremiumModifierAPISerializer().data)

    def post(self, request, *args, **kwargs):
        serializer = PremiumModifierAPISerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        premium = serializer.mod_premium()
        return Response(premium)