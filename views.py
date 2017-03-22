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
from .serializers import SubmissionDataSerializer, ContractorClassSerializer, SubmissionResponseSerializer
import json
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import logout
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import authentication, permissions
from rest_framework import status

#Here we define classes for internal use within the views
class ManualRate:
  #Each of these methods need to return the ManualRate object so they can be chained.
  def get_limit_premium(self, premium_type):
    attr = self.__getattribute__(premium_type)
    limit = Limit.objects.get(limit1__iexact = self.limit1, limit2__iexact = self.limit2)
    value = attr * limit.factor
    print("Start Value: %s Factor: %s End Value: %s" % (attr, limit.factor, value))
    self.__setattr__(premium_type, value)
    return self
  
  def get_deductible_premium(self, premium_type):
    attr = self.__getattribute__(premium_type)
    deductible = Deductible.objects.get(deductible__iexact = self.deductible)    
    value = attr * deductible.factor
    print("Start Value: %s Factor: %s End Value: %s" % (attr, deductible.factor, value))
    self.__setattr__(premium_type, value)
    return self
  
  def get_primary_nose_coverage_premium(self, premium_type):
    attr = self.__getattribute__(premium_type)
    primary_nose_coverage = Nose.objects.get(years__iexact = self.primary_nose_coverage)
    value = attr * primary_nose_coverage.factor 
    print("Start Value: %s Factor: %s End Value: %s" % (attr, primary_nose_coverage.factor, value))
    self.__setattr__(premium_type, value)
    return self
  
  def get_mold_nose_coverage_premium(self, premium_type):
    attr = self.__getattribute__(premium_type)
    nose = Nose.objects.get(years__iexact = self.mold_nose_coverage)
    value = attr * nose.factor
    print("Start Value: %s Factor: %s End Value: %s" % (attr, nose.factor, value))
    self.__setattr__(premium_type, value)
    return self
  
  def __init__(self, base_rate_premium_totals, manual_rate_data):
    self.total_ex_mold_premium = base_rate_premium_totals.total_premium_ex_mold
    self.total_mold_premium = base_rate_premium_totals.total_mold_premium
    for k in manual_rate_data:
      #These are the keys we are looking for, ignore excess data or deal with it later
      if k in ('limit1', 'limit2', 'deductible', 'primary_nose_coverage', 'mold_nose_coverage'): 
        setattr(self, k, manual_rate_data[k])
        #This is gross and can probably be refactored, but you kick off the chain by passing the object to the class to perform the calculations. The return value of each is the object.
    self.total_ex_mold_premium = ManualRate.get_limit_premium(self, 'total_ex_mold_premium').get_deductible_premium('total_ex_mold_premium').get_primary_nose_coverage_premium('total_ex_mold_premium').total_ex_mold_premium 
    self.total_mold_premium = ManualRate.get_limit_premium(self, 'total_mold_premium').get_deductible_premium('total_mold_premium').get_mold_nose_coverage_premium('total_mold_premium').total_mold_premium

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

#@method_decorator(csrf_exempt, name='dispatch')  
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