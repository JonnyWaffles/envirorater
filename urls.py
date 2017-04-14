from django.conf.urls import url, include
from rest_framework import routers, serializers, viewsets
from rest_framework.urlpatterns import format_suffix_patterns

from .views import (Index, SubmissionViewSet, ContractorClassViewSet, ProfessionalClassViewSet,
                    PremiumModifierAPI, UserViewSet, CoverageViewSet, BaseRatingUnitViewSet)

router = routers.DefaultRouter()

router.register(r'submissions', SubmissionViewSet, base_name = "submissions")
router.register(r'contractors', ContractorClassViewSet)
router.register(r'professionals', ProfessionalClassViewSet)
router.register(r'users', UserViewSet)


urlpatterns = [
    url(r'^factor/$', PremiumModifierAPI.as_view(), name='premium-modifier-api'),
    url(r'^', include(router.urls)),
    url(r'submissions/(?P<submission_set>\d+)/cpl$', CoverageViewSet.as_view({'get' : 'cpl_details'}), name='cpl-details'),
    url(r'submissions/(?P<submission_set>\d+)/pro$', CoverageViewSet.as_view({'get' : 'pro_details'}), name='pro-details'),
    url(r'submissions/(?P<submission_set>\d+)/(?P<submission_type>.*)/units', BaseRatingUnitViewSet.as_view({'get' : 'list'}), name='cpl-units-list'),    
]