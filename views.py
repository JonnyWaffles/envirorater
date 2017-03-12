from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic.list import ListView 
from django.views.generic import View
from django.forms import inlineformset_factory, formset_factory
from django.http import HttpResponseRedirect, JsonResponse
from .models import ContractorClass, RevenueBand, MoldHazardGroup, Limit, Deductible, Aggregate, Nose

# Create your views here.
class ContractorClassBaseRate:
  def __init__(self, contractor_class, class_revenue, mold_hazard_group):  
    contractor_class = ContractorClass.objects.get(iso_code__iexact = contractor_class)
    revenue_band = RevenueBand.objects.get(start__lt = class_revenue, end__gte = class_revenue)
    self.iso_code = contractor_class.iso_code
    self.premium_ex_mold = contractor_class.get_premium_ex_mold(class_revenue, revenue_band)
    self.mold_premium = contractor_class.get_mold_premium(class_revenue, revenue_band, mold_hazard_group)
    self.premium = contractor_class.get_total_premium(class_revenue, revenue_band, mold_hazard_group)
  
  def __str__(self):
    return "ISO Code: %s Premium: %s" % (self.iso_code, self.premium)

class Index(View):    
  def get(self, request, *args, **kwargs):
    contractor_classes = ContractorClass.objects.all()
    context = ''
    return render(request, 'envirorater/home.html', context)