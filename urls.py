from django.conf.urls import url, include
from rest_framework import routers, serializers, viewsets
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.documentation import include_docs_urls

from .views import (SubmissionSetViewSet, ContractorClassViewSet, ProfessionalClassViewSet,
                    PremiumModifierAPI, UserViewSet, CPLSubmissionViewSet, ProfessionalSubmissionViewSet,
                    CPLBaseRatingUnitViewSet, CPLBaseRatingUnitViewSet, ProfessionalBaseRatingUnitViewSet,
                    ProfessionalRevenueBandViewSet, ContractorsPollutionRevenueBandViewSet, DeductibleViewSet,
                    PriorActsViewSet, AggregateViewSet, StateViewSet, NoseViewSet, LimitViewSet,
                    CPLSubmissionManualRateViewSet, ProfessionalSubmissionManualRateViewSet, api_root)

router = routers.SimpleRouter()

router.register(r'submissions', SubmissionSetViewSet, base_name = "submissions")
router.register(r'contractors', ContractorClassViewSet)
router.register(r'professionals', ProfessionalClassViewSet)
router.register(r'users', UserViewSet)
router.register(r'pro-revenue-bands', ProfessionalRevenueBandViewSet)
router.register(r'cpl-revenue-bands', ContractorsPollutionRevenueBandViewSet)
router.register(r'deductibles', DeductibleViewSet)
router.register(r'prior-acts', PriorActsViewSet)
router.register(r'aggregates', AggregateViewSet)
router.register(r'state', StateViewSet)
router.register(r'nose', NoseViewSet)
router.register(r'limit', LimitViewSet)



cpl_submission_viewset = CPLSubmissionViewSet.as_view({'get' : 'retrieve', 
                                                       'put' : 'update',
                                                       'patch' : 'partial_update',
                                                       'delete' : 'destroy'})

professional_submission_viewset = ProfessionalSubmissionViewSet.as_view({'get' : 'retrieve',
                                                                         'put' : 'update',
                                                                         'patch' : 'partial_update',
                                                                         'delete' : 'destroy'})

cpl_units_list = CPLBaseRatingUnitViewSet.as_view({'get' : 'list',
                                                   'post' : 'create'})

pro_units_list = ProfessionalBaseRatingUnitViewSet.as_view({'get' : 'list',
                                                            'post' : 'create'})

cpl_units_detail = CPLBaseRatingUnitViewSet.as_view({'get': 'retrieve',
                                                     'put': 'update',
                                                     'patch': 'partial_update',
                                                     'delete': 'destroy'})

pro_units_detail = ProfessionalBaseRatingUnitViewSet.as_view({'get': 'retrieve',
                                                     'put': 'update',
                                                     'patch': 'partial_update',
                                                     'delete': 'destroy'})

cpl_manual_rate_detail = CPLSubmissionManualRateViewSet.as_view({'get' : 'retrieve',
                                                                 'post' : 'create',
                                                                'put' : 'update',
                                                                'patch' : 'partial_update',
                                                                'delete' : 'destroy'})

pro_manual_rate_detail = ProfessionalSubmissionManualRateViewSet.as_view({'get' : 'retrieve',
                                                                          'post' : 'create',
                                                                          'put' : 'update',
                                                                          'patch' : 'partial_update',
                                                                          'delete' : 'destroy'})

urlpatterns = [
    url(r'^$', api_root),
    url(r'^', include(router.urls)),
    url(r'^modifier/$', PremiumModifierAPI.as_view(), name='premium-modifier-api'),
    url(r'^docs/', include_docs_urls(title='Envirorater API')),
    url(r'submissions/(?P<submission_set>\d+)/cpl$', cpl_submission_viewset, name='cpl-details'),
    url(r'submissions/(?P<submission_set>\d+)/pro$', professional_submission_viewset, name='pro-details'),
    url(r'submissions/(?P<submission_set>\d+)/cpl/units$', cpl_units_list, name='cpl-units-list'),    
    url(r'submissions/(?P<submission_set>\d+)/pro/units$', pro_units_list, name='pro-units-list'), 
    url(r'submissions/(?P<submission_set>\d+)/cpl/units/(?P<iso_code>\d+)/', cpl_units_detail, name='cpl-units-detail'),
    url(r'submissions/(?P<submission_set>\d+)/pro/units/(?P<iso_code>\d+)/', pro_units_detail, name='pro-units-detail'),
    url(r'submissions/(?P<submission_set>\d+)/cpl/manual_rate/', cpl_manual_rate_detail, name='cpl-manual-rate-detail'),
    url(r'submissions/(?P<submission_set>\d+)/pro/manual_rate/', pro_manual_rate_detail, name='pro-manual-rate-detail'),
]
