from django.contrib import admin
from envirorater.models import ContractorClass, RevenueBand, MoldHazardGroup, Limit, Deductible, Aggregate, Nose
# Register your models here.
admin.site.register(ContractorClass)
admin.site.register(RevenueBand)
admin.site.register(MoldHazardGroup)
admin.site.register(Limit)
admin.site.register(Deductible)
admin.site.register(Aggregate)
admin.site.register(Nose)