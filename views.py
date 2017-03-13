from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.list import ListView 
from django.views.generic import View
from django.forms import inlineformset_factory, formset_factory
from django.http import HttpResponseRedirect, JsonResponse
from django.core import serializers
from decimal import Decimal
from .models import ContractorClass, RevenueBand, MoldHazardGroup, Limit, Deductible, Aggregate, Nose
import json

# Create your views here.
class ContractorClassBaseRate:
  def __init__(self, iso_code, class_revenue, mold_hazard_group):
    iso_code = int(iso_code)
    class_revenue = int(class_revenue)
    contractor_class = ContractorClass.objects.get(iso_code__iexact = iso_code)
    self.iso_code = contractor_class.iso_code
    self.premium_ex_mold = contractor_class.get_premium_ex_mold(class_revenue)
    self.mold_premium = contractor_class.get_mold_premium(class_revenue, mold_hazard_group)
    self.premium = contractor_class.get_total_premium(class_revenue, mold_hazard_group)
  
  def __str__(self):
    return "ISO Code: %s Premium: %s" % (self.iso_code, self.premium)
  
class Index(View):    
  def get(self, request, *args, **kwargs):
    contractor_classes = ContractorClass.objects.all()
    context = {"contractor_classes" : contractor_classes}
    return render(request, 'envirorater/home.html', context)  

class ContractorBaseRateAPI(View):    
#   Provide a GET request with iso_code, class_revenue, and mold_hazard_group
#   Returns JsonResponse with contractor class key values
    
    def get(self, request, *args, **kwargs):
      request_dictionary = request.GET.dict()
      contractor_class = ContractorClassBaseRate(**request_dictionary)
      return JsonResponse(contractor_class.__dict__)