from django.conf.urls import url

from .views import Index, ContractorBaseRateAPI, ProfessionalBaseRateAPI, PremiumModifierAPI, SubmissionAPI

urlpatterns = [
    url(r'^$', Index.as_view(), name='index'),
    url(r'^api/$', SubmissionAPI.as_view(), name='submission-api'),
    url(r'^api/contractor/$', ContractorBaseRateAPI.as_view(), name='contractor-base-rate-api'),
    url(r'^api/professional/$', ProfessionalBaseRateAPI.as_view(), name='professional-base-rate-api'),
    url(r'^api/factor/$', PremiumModifierAPI.as_view(), name='premium-modifier-api'),    
]