from django import forms
from .models import ContractorClass, ContractorsPollutionRevenueBand, ProfessionalRevenueBand, MoldHazardGroup, Limit, Deductible, Aggregate, Nose

class ContractorClassForm(forms.Form):
  iso_code = forms.IntegerField(label = "ISO Code")
  class_revenue = forms.IntegerField(label = "Revenue")
  mold_hazard_group = forms.CharField(label = "Mold Hazard Group")
    