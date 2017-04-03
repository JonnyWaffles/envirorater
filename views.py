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
from .models import (ContractorClass, ProfessionalClass, ContractorsPollutionRevenueBand, ProfessionalRevenueBand,
                     MoldHazardGroup, Limit, Deductible, Aggregate, Nose, PriorActs, State)
from .serializers import (CPLBaseRatingClassDataSerializer, CPLManualRateDataSerializer, CPLSubmissionDataSerializer,
                          CPLPremiumModifierAPISerializer, ProfessionalBaseRatingClassDataSerializer, 
                          ProfessionalManualRateDataSerializer, ProfessionalSubmissionDataSerializer, 
                          ProfessionalPremiumModifierAPISerializer, CPLManualRateResponseSerializer,
                          ContractorBaseRateSerializer, CPLSubmissionResponseSerializer, ProfessionalBaseRateSerializer, 
                          ContractorClassSerializer, ProfessionalClassSerializer)
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
import rest_framework.serializers
import importlib

#Here we define classes for internal use within the views
class PremiumModifier: #Or, Manual rate cleaner try number 2?
    models_module = importlib.import_module("envirorater.models")
  
    @staticmethod
    def mod_premium(premium, **factor_dict):
        def get_rating_factors(**factor_dict):
            #Check for various types, we can add more later as needed.  Excess k:v
            #pairs will be ignored
            #Also map the types to their respective models
            factor_types = {'deductible' : 'Deductible', 'primary_nose_coverage' : 'Nose', 'mold_nose_coverage' : 'Nose', 
                              'aggregate_deductible_multiplier' : 'Aggregate', 'state' : 'State', 'prior_acts_years' : 'PriorActs' }
            factor_value_dict = {}
            for k in factor_dict:
                if k in factor_types.keys():
                    query = {'{0}__iexact'.format(k) : factor_dict[k]}
                    factor = getattr(PremiumModifier.models_module, factor_types[k]).objects.get(**query).factor
                    factor_value_dict.update({k : factor})
              #Limit factor is a special case that needs two values from the
              #dictionary, so we get it outside of the prior statements since we need
              #both
                if 'limit1' in factor_dict.keys() and 'limit2' in factor_dict.keys():
                    limit_factor = Limit.objects.get(limit1__iexact = factor_dict['limit1'], limit2__iexact = factor_dict['limit2']).factor
                    factor_value_dict.update({'limit' : limit_factor})
            return factor_value_dict    
            #debug
        factor_value_dict = get_rating_factors(**factor_dict)
        for factor in factor_value_dict.values():
            premium = premium * factor
        return premium

#Base Class for Submission specific manual rates.
class ManualRate:
#all ManualRates may these keys
    key_list = ('limit1', 'limit2', 'deductible')
    def __init__(self, manual_rate_data, **kwargs):
        for k in manual_rate_data:
        #These are the keys we are looking for, ignore excess data or deal with
        #it later.
        #Set the attributes for easy response serialization
            if k in self.__class__.key_list: 
                setattr(self, k, manual_rate_data[k])
class ProfessionalManualRate(ManualRate):
    key_list = ManualRate.key_list + ('aggregate_deductible_multiplier', 'state', 'prior_acts_years')

    def __init__(self, manual_rate_data, **kwargs):
        super().__init__(self, manual_rate_data, **kwargs)
        if 'totals' in kwargs:
            try:
                professional_base_rate_premium_totals_instance = kwargs['totals']
                self.premium = PremiumModifier.mod_premium(professional_base_rate_premium_totals_instance.premium, self.__dict__)
            except AttributeError:
                print("Object has no attribute Premium")
                
class CPLManualRate(ManualRate):
    key_list = ManualRate.key_list + ('primary_nose_coverage', 'mold_nose_coverage')

    def __init__(self, manual_rate_data, **kwargs):
        super().__init__(manual_rate_data, **kwargs)
        if 'totals' in kwargs:
                contractor_base_rate_premium_totals_instance = kwargs['totals']
                ex_mold_dict = {k : manual_rate_data[k] for k in manual_rate_data.keys() & {'limit1', 'limit2', 'deductible', 'primary_nose_coverage'} }
                mold_dict = {k : manual_rate_data[k] for k in manual_rate_data.keys() & {'limit1', 'limit2', 'deductible', 'mold_nose_coverage'} }
                self.total_premium_ex_mold = PremiumModifier.mod_premium(contractor_base_rate_premium_totals_instance.total_premium_ex_mold, **ex_mold_dict)
                self.total_mold_premium = PremiumModifier.mod_premium(contractor_base_rate_premium_totals_instance.total_mold_premium, **mold_dict)
            
class ContractorBaseRate:
    def __init__(self, iso_code, revenue, mold_hazard_group):
        contractor_class = ContractorClass.objects.get(iso_code__iexact = iso_code)
        self.revenue = revenue
        self.mold_hazard_group = mold_hazard_group
        self.iso_code = contractor_class.iso_code
        self.premium_ex_mold = contractor_class.get_premium_ex_mold(revenue)
        self.mold_premium = contractor_class.get_mold_premium(revenue, mold_hazard_group)
        self.premium = contractor_class.get_total_premium(revenue, mold_hazard_group)
  
    def __str__(self):
        return "ISO Code: %s Premium: %s" % (self.iso_code, self.premium)
    
class ProfessionalBaseRate:
    def __init__(self, iso_code, revenue):
        professional_class = ProfessionalClass.objects.get(iso_code__iexact = iso_code)
        self.iso_code = professional_class.iso_code
        self.premium = professional_class.get_premium(revenue)
    
    def __str__(self):
        return "ISO Code: %s Premium: %s" % (self.iso_code, self.premium)

class ContractorBaseRatePremiumTotals:
    def __init__(self, submission):
        self.total_premium_ex_mold = 0
        self.total_mold_premium = 0
        for base_rating_unit in submission.base_rating_classes:
            self.total_premium_ex_mold += base_rating_unit.premium_ex_mold
            self.total_mold_premium += base_rating_unit.mold_premium
            self.total_premium = self.total_premium_ex_mold + self.total_mold_premium
    
    def __str__(self):
        return "Primary Premium: %s Mold Premium: %s Total: %s" % (self.total_premium_ex_mold, self.total_mold_premium, self.total_premium)

class ProfessionalBaseRatePremiumTotals:
    def __init__(self, submission):
        self.total_premium = 0
        for base_rating_unit in submission.base_rating_classes:
            self.total_premium += base_rating_unit.premium
    

#Creating a skeleton abstract submission since both types have a sub_type...,
#base_rating classes, and manual_rate
#There's probably a better way to do this and may need to be refactored later
class Submission:
  #Child classes have to overwrite these values to use the right classes
#   rating_class = None
#   base_rating_total_class = None
#   manual_rate_class = None
    def __init__(self, submission_data, sub_type):
    #We need to set the sub_type for the response serializer
        self.sub_type = sub_type
        self.base_rating_classes = []
        base_rating_array = submission_data['base_rating_classes']
        rating_class = self.rating_class   
        for base_rating_unit in base_rating_array:
    #This is where we change the BaseRater depending on submission class
    #I assume there is a better way other than hardcoding the appropriate
    #BaseRater class.
            unit = rating_class(**base_rating_unit) #Unpack data to instantiate the objects
            self.base_rating_classes.append(unit)        
        base_rate_premium_totals = self.base_rating_total_class(self)  
    #Need to refactor ManualRate to not be Submission Type specific.
        self.manual_rate = self.manual_rate_class(submission_data['manual_rate'], totals = base_rate_premium_totals) 
    
class CPLSubmission(Submission):
    rating_class = ContractorBaseRate
    base_rating_total_class = ContractorBaseRatePremiumTotals
    manual_rate_class = CPLManualRate

class ProfessionalSubmission(Submission):
    rating_class = ProfessionalBaseRate
    base_rating_total_class = ProfessionalBaseRatePremiumTotals
    manual_rate_class = ProfessionalManualRate
      
#Views go here.
class Index(View):    
    def get(self, request, *args, **manual_rate_data):
        contractor_classes = ContractorClass.objects.all()    
        context = {"contractor_classes" : contractor_classes}    
        return render(request, 'envirorater/home.html', context)

class ContractorBaseRateAPI(APIView):    
#   Provide a GET request with iso_code, revenue, and mold_hazard_group
#   Returns JsonResponse with contractor class key values
#   Note need to use REST Framework to surprass the Cross Origin Problem
    permission_classes = (permissions.AllowAny,)
    
    def get(self, request, *args, **manual_rate_data): #Need to check on manual_rate_data how did this get here?
        contractor_classes = ContractorClass.objects.all()
        serializer = ContractorClassSerializer(contractor_classes, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **manual_rate_data):
        submission_data = request.data
        cpl_serializer = CPLSubmissionDataSerializer(data = submission_data.get('cpl_submission'))
        if cpl_serializer.is_valid():
      #Note later need to come back here and do for each key() in
      #submission_data so we can do more than 1 sub type per request.
            cpl_submission = CPLSubmission(cpl_serializer.validated_data, 'cpl_submission')
            return Response(CPLSubmissionResponseSerializer(cpl_submission).data)
        else:
            return Response(cpl_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ProfessionalSubmissionAPI(APIView):
  
  permission_classes = (permissions.AllowAny,)
  
  def get(self, request, *args, **kwargs):
    professional_classes = ProfessionalClass.objects.all()
    serializer = ProfessionalClassSerializer(professional_classes, many=True)
    return Response(serializer.data)

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
            print('Premium In: %s' % (premium))
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
                    limit_factor = Limit.objects.get(limit1__iexact = limit1, limit2__iexact = limit2).factor
                except ObjectDoesNotExist:
                    raise rest_framework.serializers.ValidationError('That limit object could not be found')                
                factor_dict = {'limit1' : limit2, 'limit2' : limit2}      
            else:
                factor_dict = {query.data['modifier'] : query.data['mod_value']}
                premium = PremiumModifiers().mod_premium(premium, **factor_dict)
                query._data['premium'] = premium
                return Response(query.data)
        else:
      #Note there has to be a better way to show an example
            raise rest_framework.serializers.ValidationError('Please make factor GET requests with premium, modifier, and mod_value arguments.')
			