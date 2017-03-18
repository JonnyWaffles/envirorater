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
import json
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import logout

# Create your views here.
class ContractorBaseRate:
  def __init__(self, iso_code, revenue, mold_hazard_group):
    iso_code = int(iso_code)
    revenue = int(revenue)
    contractor_class = ContractorClass.objects.get(iso_code__iexact = iso_code)
    self.iso_code = contractor_class.iso_code
    self.premium_ex_mold = contractor_class.get_premium_ex_mold(revenue)
    self.mold_premium = contractor_class.get_mold_premium(revenue, mold_hazard_group)
    self.premium = contractor_class.get_total_premium(revenue, mold_hazard_group)
  
  def __str__(self):
    return "ISO Code: %s Premium: %s" % (self.iso_code, self.premium)

class Submission:  
  def __init__(self, submission_data, type):     
    self.type = type
    self.contractor_classes = []
    contractor_array = submission_data[type]['contractor_classes']
    for contractor_data in contractor_array:
      c = ContractorBaseRate(**contractor_data)
      self.contractor_classes.append(c)
    self.manual_rate = submission_data[type]['manual_rate'] 
  
class Index(View):    
  def get(self, request, *args, **kwargs):
    contractor_classes = ContractorClass.objects.all()    
    context = {"contractor_classes" : contractor_classes}    
    return render(request, 'envirorater/home.html', context)

@method_decorator(csrf_exempt, name='dispatch')
class ContractorBaseRateAPI(View):    
#   Provide a GET request with iso_code, revenue, and mold_hazard_group
#   Returns JsonResponse with contractor class key values
#   Note need to use REST Framework to surprass the Cross Origin Problem
    
    def get(self, request, *args, **kwargs):
      request_dictionary = request.GET.dict()
      contractor_class = ContractorBaseRate(**request_dictionary)
      return JsonResponse(contractor_class.__dict__)
    
    def post(self, request, *args, **kwargs):
      submission_data = json.loads(request.body)
      submission = Submission(submission_data, 'cpl_submission')
      print(submission)
      return JsonResponse(submission, safe=False)
        
      
      
 