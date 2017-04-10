from django.conf.urls import url, include
from rest_framework import routers, serializers, viewsets
from rest_framework.urlpatterns import format_suffix_patterns

from .views import Index, SubmissionViewSet, ContractorClassViewSet, ProfessionalClassViewSet, PremiumModifierAPI, UserViewSet

router = routers.DefaultRouter()

router.register(r'submissions', SubmissionViewSet, base_name = "submissions")
router.register(r'contractors', ContractorClassViewSet)
router.register(r'professionals', ProfessionalClassViewSet)
router.register(r'users', UserViewSet)

urlpatterns = [
    url(r'^factor/$', PremiumModifierAPI.as_view(), name='premium-modifier-api'),
    url(r'^', include(router.urls)),
]