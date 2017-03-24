from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.list import ListView 
from django.views.generic import View
from django.forms import inlineformset_factory, formset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.core import serializers
from decimal import Decimal
from .forms import ContractorClassForm
from .models import ContractorClass, RevenueBand, MoldHazardGroup, Limit, Deductible, Aggregate, Nose
from .serializers import SubmissionDataSerializer, ContractorClassSerializer, SubmissionResponseSerializer, PremiumModifierAPISerializer
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

class PremiumModifiers: #Or, Manual rate cleaner try number 2?
  models_module = importlib.import_module("envirorater.models")
  
  def get_rating_factors(self, **factor_dict):
    #Check for various types, we can add more later as needed. Excess k:v pairs will be ignored
    #Also map the types to their respective models
    factor_types = {'deductible' : 'Deductible', 'primary_nose_coverage' : 'Nose', 'mold_nose_coverage' : 'Nose' }
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

class ContractorBaseRate:
  def __init__(self, iso_code, revenue, mold_hazard_group):
    contractor_class = ContractorClass.objects.get(iso_code__iexact = iso_code)
    self.iso_code = contractor_class.iso_code
    self.premium_ex_mold = contractor_class.get_premium_ex_mold(revenue)
    self.mold_premium = contractor_class.get_mold_premium(revenue, mold_hazard_group)
    self.premium = contractor_class.get_total_premium(revenue, mold_hazard_group)
  
  def __str__(self):
    return "ISO Code: %s Premium: %s" % (self.iso_code, self.premium)

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
    self.contractor_classes = []
    contractor_array = submission_data['contractor_classes']
    for contractor_data in contractor_array:
      c = ContractorBaseRate(**contractor_data) #Unpack data to instantiate the objects
      self.contractor_classes.append(c)
    base_rate_premium_totals = BaseRatePremiumTotals(self)  
    self.manual_rate = ManualRate(base_rate_premium_totals, submission_data['manual_rate']) 
    
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
    
  def get(self, request, *args, **manual_rate_data):
    contractor_classes = ContractorClass.objects.all()
    serializer = ContractorClassSerializer(contractor_classes, many=True)
    return Response(serializer.data)

  def post(self, request, *args, **manual_rate_data):
    submission_data = request.data
    serializer = SubmissionDataSerializer(data = submission_data.get('cpl_submission'))
    if serializer.is_valid():
      #Note later need to come back here and do for each key() in submission_data so we can do more than 1 sub type per request.
      submission = Submission(serializer.validated_data, 'cpl_submission')
      return Response(SubmissionResponseSerializer(submission).data)
    else:
      return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PremiumModifierAPI(APIView):
  permission_classes = (permissions.AllowAny, )
  def get(self, request, *args, **kwargs):
    #Need to come back here and figure out how to display an example
    return Response(PremiumModifierAPISerializer().data)
    
class PremiumModifierAPIGet(APIView):  
  permission_classes = (permissions.AllowAny, )
  from rest_framework.exceptions import ValidationError
  
  def get(self, request, *args, **kwargs):
    query = PremiumModifierAPISerializer(request.query_params)
    premium = query.data['premium']
    print('Premium In: %s' % (premium))
    factor_dict = {}
    #Once again limits are a special case. We need the user to input them 'limit1/limit2'
    if query.data['modifier'] == 'limit':
      try:
        data_string = query.data['mod_value']
        limit1 = data_string.split('/')[0]
        limit2 = data_string.split('/')[1]
        #for debug
        print("Limit1: %s" % (limit1) )
        print("Limit2: %s" % (limit2) )
        factor_dict = {'limi1t' : limit2, 'limit2' : limit2}
      except:
        raise rest_framework.serializers.ValidationError('Limits must be separated by a slash. Ex. 10000/5000')
    factor_dict = {query.data['modifier'] : query.data['mod_value']}
    premium = PremiumModifiers().mod_premium(premium, **factor_dict)
    print('New Premium: %s' % (premium))
    query._data['premium'] = premium
    print(query)
    return Response(query.data)