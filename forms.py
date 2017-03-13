from django import forms
from .models import ContractorClass, RevenueBand, MoldHazardGroup, Limit, Deductible, Aggregate, Nose

class ContractorClassForm(forms.ModelForm):
  class Meta:
    model = ContractorClass
    