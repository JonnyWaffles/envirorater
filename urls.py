from django.conf.urls import url

from . import views
from .views import Index, ContractorBaseRateAPI, PremiumModifierAPI, PremiumModifierAPIGet

urlpatterns = [
    url(r'^$', Index.as_view(), name='index'),
    url(r'^api/$', ContractorBaseRateAPI.as_view(), name='contractor-base-rate-api'),
    url(r'^api/factor/$', PremiumModifierAPI.as_view(), name='premium-modifier-api'),
    url(r'^api/factor/lookup/$', PremiumModifierAPIGet.as_view(), name='premium-modifier-api-get'),
]