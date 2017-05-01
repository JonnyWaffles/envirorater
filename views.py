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
                          PriorActsSerializer, AggregateSerializer, StateSerializer, NoseSerializer, LimitSerializer)
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
		
#Views go here.
class Index(View):    
    def get(self, request, *args, **manual_rate_data):
        contractor_classes = ContractorClass.objects.all()    
        context = {"contractor_classes" : contractor_classes}    
        return render(request, 'envirorater/home.html', context)
    
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

class BulkCreateMixin:
    """
    This Mixin checks the view's data and returns the ListSerializer
    whenever an array is posted.
    """
    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            data = kwargs["data"]

            if isinstance(data, list):
                kwargs["many"] = True

        return super().get_serializer(*args, **kwargs)

class AdminOnlyViewMixin:

    permission_classes = (permissions.IsAdminUser, )


class UserViewSet(viewsets.ModelViewSet):

	queryset = User.objects.all()
	serializer_class = UserSerializer
	permission_classes = (permissions.AllowAny, )

class SubmissionSetViewSet(BulkCreateMixin, viewsets.ModelViewSet):

    queryset = SubmissionSet.objects.all().order_by('-id')
    serializer_class = SubmissionSetSerializer
    permission_classes = (permissions.AllowAny, )

    def perform_create(self, serializer):
        
        if not isinstance(serializer, ListSerializer):
            serializer.save(owner = self.request.user, raw = self.request.data.get('raw', False))
        else:
            serializer.save(owner = self.request.user)

    def perform_update(self, serializer):
        serializer.save(owner = self.request.user, raw = self.request.data.get('raw', False))

class CPLSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.AllowAny,)
    queryset = CPLSubmission.objects.all()

    serializer_class = CPLSubmissionSerializer

    def get_object(self):
        submission_set = get_object_or_404(SubmissionSet, id = self.kwargs['submission_set'])
        return submission_set.cpl_submission


    def perform_update(self, serializer):
        serializer.save(raw = self.request.data.get('raw', False))

class ProfessionalSubmissionViewSet(viewsets.ModelViewSet):
    permission_classes = (permissions.AllowAny,)
    queryset = ProfessionalSubmission.objects.all()

    serializer_class = ProfessionalSubmissionSerializer
     
    def get_object(self):
        submission_set = get_object_or_404(SubmissionSet, id = self.kwargs['submission_set'])
        return submission_set.professional_submission

    def perform_update(self, serializer):
        serializer.save(raw = self.request.data.get('raw', False))
        
class CPLBaseRatingUnitViewSet(BulkCreateMixin, viewsets.ModelViewSet):

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

class ProfessionalBaseRatingUnitViewSet(BulkCreateMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return the ProfessionalBaseRating Unit by iso_code.

    update:
    Update's the ProfessionalBaseRating Unit.

    patch:
    Partially update's the ProfessionalBaseRating Unit.

    destroy:
    Delete's the ProfessionalBaseRating Unit
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


class ContractorClassViewSet(BulkCreateModelMixin, viewsets.ModelViewSet):

	permission_classes = (permissions.AllowAny,)

	queryset = ContractorClass.objects.all()
	serializer_class = ContractorClassSerializer
	lookup_field = 'iso_code'
    
class ProfessionalClassViewSet(BulkCreateMixin, viewsets.ModelViewSet):

    permission_classes = (permissions.AllowAny,)

    queryset = ProfessionalClass.objects.all()
    serializer_class = ProfessionalClassSerializer
    lookup_field = 'iso_code'

class ProfessionalRevenueBandViewSet(BulkCreateMixin, viewsets.ModelViewSet):

    queryset = ProfessionalRevenueBand.objects.all()
    serializer_class = ProfessionalRevenueBandSerializer

class ContractorsPollutionRevenueBandViewSet(BulkCreateMixin, viewsets.ModelViewSet):

    queryset = ContractorsPollutionRevenueBand.objects.all()
    serializer_class = ContractorsPollutionRevenueBandSerializer

class DeductibleViewSet(BulkCreateMixin, viewsets.ModelViewSet):

    queryset = Deductible.objects.all()
    serializer_class = DeductibleSerializer

class LimitViewSet(BulkCreateMixin, viewsets.ModelViewSet):

    queryset = Limit.objects.all()
    serializer_class = LimitSerializer

class PriorActsViewSet(BulkCreateMixin, viewsets.ModelViewSet):

    queryset = PriorActs.objects.all()
    serializer_class = PriorActsSerializer

class AggregateViewSet(BulkCreateMixin, viewsets.ModelViewSet):

    queryset = Aggregate.objects.all()
    serializer_class = AggregateSerializer

class StateViewSet(BulkCreateMixin, viewsets.ModelViewSet):

    queryset = State.objects.all()
    serializer_class = StateSerializer

class NoseViewSet(BulkCreateMixin, viewsets.ModelViewSet):

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