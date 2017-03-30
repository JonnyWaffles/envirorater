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
from .models import ContractorClass, ProfessionalClass, RevenueBand, MoldHazardGroup, Limit, Deductible, Aggregate, Nose, PriorActs, State
from .serializers import CPLSubmissionDataSerializer, ContractorClassSerializer, SubmissionResponseSerializer, PremiumModifierAPISerializer, ProfessionalClassSerializer
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
from abc import 
import rest_framework.serializers
import importlib

#Here we define classes for internal use within the views

class PremiumModifiers: #Or, Manual rate cleaner try number 2?
  models_module = importlib.import_module("envirorater.models")
  
  def get_rating_factors(self, **factor_dict):
    #Check for various types, we can add more later as needed. Excess k:v pairs will be ignored
    #Also map the types to their respective models
    factor_types = {'deductible' : 'Deductible', 'primary_nose_coverage' : 'Nose', 'mold_nose_coverage' : 'Nose', 
                    'aggregate_deductible_multiplier' : 'Aggregate', 'state' : 'State', 'prior_acts_years' : 'PriorActs' }
    factor_value_dict = {}
    for k in factor_dict:
      if k in factor_types.keys():
        query = {'{0}__iexact'.format(k) : factor_dict[k]}
        factor = getattr(PremiumModifiers.models_module, factor_types[k]).objects.get(**query).factor
        factor_value_dict.update( {k : factor} )
    #Limit factor is a special case that needs two values from the dictionary, so we get it outside of the prior statements since we need both
    if 'limit1' in factor_dict.keys() and 'limit2' in factor_dict.keys():
        limit_factor = Limit.objects.get(limit1__iexact = factor_dict['limit1'], limit2__iexact = factor_dict['limit2']).factor
        factor_value_dict.update({'limit' : limit_factor})
    return factor_value_dict
  
  def mod_premium(self, premium, **factor_dict):
    #debug
    print("Premium: %s" % (premium))
    print("Factor_Dict: %s" % (factor_dict))
    factor_value_dict = PremiumModifiers.get_rating_factors(self, **factor_dict)
    for factor in factor_value_dict.values():
      premium = premium * factor
    return premium

class ManualRate:  
  def __init__(self, base_rate_premium_totals, manual_rate_data):
    for k in manual_rate_data:
      #These are the keys we are looking for, ignore excess data or deal with it later.
      #Set the attributes for easy response serialization
      if k in ('limit1', 'limit2', 'deductible', 'primary_nose_coverage', 'mold_nose_coverage'): 
        setattr(self, k, manual_rate_data[k])
    #Get the rating factor dictionary    
    #There may be a way to refactor this since the only difference is the nose coverage
    ex_mold_dict = {k : manual_rate_data[k] for k in manual_rate_data.keys() & {'limit1', 'limit2', 'deductible', 'primary_nose_coverage'} }
    ex_mold_premium = base_rate_premium_totals.total_premium_ex_mold
    self.total_premium_ex_mold = PremiumModifiers().mod_premium(ex_mold_premium, **ex_mold_dict)
    mold_premium = base_rate_premium_totals.total_mold_premium
    mold_dict = {k : manual_rate_data[k] for k in manual_rate_data.keys() & {'limit1', 'limit2', 'deductible', 'mold_nose_coverage'} }
    self.total_mold_premium = PremiumModifiers().mod_premium(mold_premium, **mold_dict)
    
class ProfessionalManualRate:
  def __init__(self, base_rate_premium_totals, manual_rate_data):
    total_premium = base_rate_premium_totals.total_premium
    key_list = ('limit1', 'limit2', 'deductible', 'aggregate_deductible_multiplier', 'state', 'prior_acts_years')
    for k in manual_rate_data:
      if k in key_list
        setattr(self, k, manual_rate_data[k])
    factor_dict = {k : manual_rate_data[k] for k in key_list}
    self.total_premium = PremiumModifiers().mod_premium(total_premium, **factor_dict)

class ContractorBaseRate:
  def __init__(self, iso_code, revenue, mold_hazard_group):
    contractor_class = ContractorClass.objects.get(iso_code__iexact = iso_code)
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

class ProfessionalBaseRatePremiumTotals:
  def __init__(self, submission)
  self.total_premium = 0
  for contractor in submission.contractor_classes:
    self.total_premium += contractor.premium

class ProfessionalSubmission:
  def __init__(self, submission_data, sub_type):
    self.sub_type = sub_type
    self.professional_classes = []
    professional_array = submission_data['contractor_classes'] #we can just call it contractor classes for now 
    for professional_data in professional_array:
      p = ProfessionalBaseRate(**professional_data)
      self.professional_classes.append(p)
    self.base_rate_premium_totals = ProfessionalBaseRatePremiumTotals(self)
    self.manual_rate = ProfessionalManualRate(base_rate_premium_totals, submission_data['manual_rate'])
    
class BaseRatePremiumTotals:
  def __init__(self, submission):
    self.total_premium_ex_mold = 0
    self.total_mold_premium = 0
    for contractor in submission.contractor_classes:
      self.total_premium_ex_mold += contractor.premium_ex_mold
      self.total_mold_premium += contractor.mold_premium
      self.total_premium = self.total_premium_ex_mold + self.total_mold_premium  
      
class Submission:  
  def __init__(self, submission_data, sub_type):
    self.sub_type = sub_type
    self.base_rating_classes = []
    base_rating_array = submission_data['base_rating_classes']
    for base_rating_unit in base_rating_array:
      unit = ContractorBaseRate(**base_rating_unit) #Unpack data to instantiate the objects
      self.base_rating_classes.append(c)
    base_rate_premium_totals = BaseRatePremiumTotals(self)  
    self.manual_rate = ManualRate(base_rate_premium_totals, submission_data['manual_rate']) 
    
class PLSubmission:
  def __init__(self, submission_data, sub_type):
    self.sub_type = sub_type
    #Note the current spreadsheet doesn't have ISO codes, but otherwise treats the PL classes the same
    #So we can use contractor classes, need to go back and refactor this DRY
    self.professional_classes = []
    
    
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
  permission_classes = (permissions.AllowAny, )
    
  def get(self, request, *args, **manual_rate_data): #Need to check on manual_rate_data how did this get here?
    contractor_classes = ContractorClass.objects.all()
    serializer = ContractorClassSerializer(contractor_classes, many=True)
    return Response(serializer.data)

  def post(self, request, *args, **manual_rate_data):
    submission_data = request.data
    cpl_serializer = CPLSubmissionDataSerializer(data = submission_data.get('cpl_submission'))
    if cpl_serializer.is_valid():
      #Note later need to come back here and do for each key() in submission_data so we can do more than 1 sub type per request.
      cpl_submission = Submission(cpl_serializer.validated_data, 'cpl_submission')
      return Response(CPLSubmissionDataSerializer(submission).data)
    else:
      return Response(cpl_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ProfessionalSubmissionAPI(APIView):
  
  permission_classes = (permissions.AllowAny, )
  
  def get(self, request, *args, **kwargs):
    professional_classes = ProfessionalClass.objects.all()
    serializer = ProfessionalClassSerializer(professional_classes, many=True)
    return Response(serializer.data)

class PremiumModifierAPI(APIView):  
  #I want a GET request with no arguments to return an options request detailing how to use the API
  #Not sure how to do that yet so need to come back to this.
  permission_classes = (permissions.AllowAny, )
  from rest_framework.exceptions import ValidationError
  
  def get(self, request, *args, **kwargs):
    if request.query_params:
      query = PremiumModifierAPISerializer(request.query_params)
      premium = query.data['premium']
      print('Premium In: %s' % (premium))
      factor_dict = {}
      #Once again limits are a special case. We need the user to input them 'limit1/limit2';
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