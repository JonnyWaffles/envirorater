from django.contrib import admin
from envirorater.models import ContractorClass, ContractorsPollutionRevenueBand, ProfessionalRevenueBand, MoldHazardGroup, Limit, Deductible, Aggregate, Nose
# Register your models here.
admin.site.register(ContractorClass)
admin.site.register(ContractorsPollutionRevenueBand)
admin.site.register(MoldHazardGroup)
admin.site.register(Limit)
admin.site.register(Deductible)
admin.site.register(Aggregate)
admin.site.register(Nose)
admin.site.register(ProfessionalRevenueBand)