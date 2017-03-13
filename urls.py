from django.conf.urls import url

from . import views
from .views import Index, ContractorBaseRateAPI

urlpatterns = [
    url(r'^$', Index.as_view(), name='index'),
    url(r'^api/$', ContractorBaseRateAPI.as_view(), name='contractor-base-rate-api'),
]