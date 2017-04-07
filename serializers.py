from rest_framework import serializers
from .models import ContractorClass, ProfessionalClass

#Note we use the PremiumModifierAPISerializer for both requests and responses by changing the _premium field.
class PremiumModifierAPISerializer(serializers.Serializer):
    choices = ['limit1', 'limit2', 'deductible', 'primary_nose_coverage', 'mold_nose_coverage','aggregate_deductible_multiplier', 'prior_acts_years']
  
    premium = serializers.IntegerField(min_value = 0)
    modifier = serializers.ChoiceField(choices)
    mod_value = serializers.CharField()

#CPL Serializers
class CPLBaseRatingClassSerializer(serializers.Serializer):
    iso_code = serializers.IntegerField(min_value = 0)
    revenue = serializers.IntegerField(min_value = 0)
    mold_hazard_group = serializers.CharField()
    premium = serializers.IntegerField(min_value = 0, default = 0, required = False, read_only = True)
    
class CPLManualRateSerializer(serializers.Serializer):
    limit1 = serializers.IntegerField(min_value = 0, default = 1000000)
    limit2 = serializers.IntegerField(min_value = 0, default = 1000000)
    deductible = serializers.IntegerField(min_value = 0, default = 10000)
    primary_nose_coverage = serializers.IntegerField(min_value = 0, default = 0)
    mold_nose_coverage = serializers.IntegerField(min_value = 0, default = 0, required = False)
    total_premium_ex_mold = serializers.IntegerField(min_value = 0, required = False, read_only = True)
    total_mold_premium = serializers.IntegerField(min_value = 0, required = False, read_only = True)  
    total_premium = serializers.IntegerField(min_value = 0, default = 0, required = False, read_only = True)

class CPLSubmissionSerializer(serializers.Serializer):
    base_rating_classes = CPLBaseRatingClassSerializer(many = True)
    manual_rate = CPLManualRateSerializer(required = False)

#Professional Serializers
class ProfessionalBaseRatingClassSerializer(serializers.Serializer):
    iso_code = serializers.IntegerField(min_value = 0, default = 222222)
    revenue = serializers.IntegerField(min_value = 0, default = 1000000)
    premium = serializers.IntegerField(min_value = 0, default = 0, required = False, read_only = True)

class ProfessionalManualRateSerializer(serializers.Serializer):
    limit1 = serializers.IntegerField(min_value = 0, default = 1000000)
    limit2 = serializers.IntegerField(min_value = 0, default = 1000000)
    deductible = serializers.IntegerField(min_value = 0, default = 10000)
    aggregate_deductible_multiplier = serializers.IntegerField(min_value = 1)
    state = serializers.CharField()
    prior_acts_years = serializers.CharField()
    total_premium = serializers.IntegerField(min_value = 0, default = 0, required = False, read_only = True)
    
class ProfessionalSubmissionSerializer(serializers.Serializer):
    base_rating_classes = ProfessionalBaseRatingClassSerializer(many = True)
    manual_rate = ProfessionalManualRateSerializer()

class ContractorClassSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ContractorClass
        fields = ( 'iso_code', 'iso_description')
    
class ProfessionalClassSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfessionalClass
        fields = ( 'iso_code', 'iso_description')

class SubmissionSetSerializer(serializers.Serializer):
    cpl_submission = CPLSubmissionSerializer(required = False)
    professional_submission = ProfessionalSubmissionSerializer(required = False)