from rest_framework import serializers
from .models import ContractorClass, ProfessionalClass

#Parent Classes, don't instantiate
class BaseRateSerializer(serializers.Serializer):
  iso_code = serializers.IntegerField(min_value = 0)
  premium = serializers.IntegerField(min_value = 0)
  
class ManualRateSerializer(serializers.Serializer):
  limit1 = serializers.IntegerField(min_value = 0)
  limit2 = serializers.IntegerField(min_value = 0)
  deductible = serializers.IntegerField(min_value = 0)
  
class BaseRatingClassSerializer(serializers.Serializer):
  iso_code = serializers.IntegerField(min_value = 0)
  revenue = serializers.IntegerField(min_value = 0)
  
class SubmissionSerializer(serializers.Serializer):
  base_rating_classes = BaseRateSerializer(many = True)
  manual_rate = ManualRateSerializer()
  
class PremiumModifierAPISerializer(serializers.Serializer):
  choices = ['limit1', 'limit2', 'deductible']
  
  premium = serializers.IntegerField(min_value = 0)
  modifier = serializers.ChoiceField(choices)
  mod_value = serializers.CharField()

#CPL Submission Serializers
class CPLBaseRatingClassDataSerializer(BaseRatingClassSerializer):
  mold_hazard_group = serializers.CharField()
  
class CPLManualRateDataSerializer(ManualRateSerializer):  
  primary_nose_coverage = serializers.IntegerField(min_value = 0)
  mold_nose_coverage = serializers.IntegerField(min_value = 0)

class CPLSubmissionDataSerializer(SubmissionSerializer):
  base_rating_classes = CPLBaseRatingClassDataSerializer(many = True)
  manual_rate = CPLManualRateDataSerializer()
  
class CPLPremiumModifierAPISerializer(PremiumModifierAPISerializer):
  choices = super().extend(['primary_nose_coverage', 'mold_nose_coverage'])
  
#Professional Submission Serializers
class ProfessionalBaseRatingClassDataSerializer(BaseRatingClassSerializer):
  #Professional can use the BaseRatingClassSerializer since it only has a code and a revenue
  #but for consistency I want to instantiate one since the above are supposed to be abstract
  pass

class ProfessionalManualRateDataSerializer(ManualRateSerializer):
  aggregate_deductible_multiplier = serializers.IntegerField(min_value = 1)
  state = serializers.CharField()
  prior_acts_years = serializers.CharField()
  
class ProfessionalSubmissionDataSerializer(SubmissionSerializer):
  base_rating_classes = ProfessionalBaseRatingClassDataSerializer(many = True)
  manual_rate = ProfessionalManualRateDataSerializer()
#Note we use the PremiumModSerializer for both requests and responses by changing the _premium field.
class ProfessionalPremiumModifierAPISerializer(PremiumModifierAPISerializer):
  choices = super().choices.extend(['aggregate_deductible_multiplier', 'prior_acts_years'])

#CPL Response Serializers
class CPLManualRateResponseSerializer(CPLManualRateDataSerializer):
  total_premium_ex_mold = serializers.IntegerField(min_value = 0)
  total_mold_premium = serializers.IntegerField(min_value = 0)  
  
class ContractorBaseRateSerializer(CPLBaseRatingClassDataSerializer):
  premium = serializers.IntegerField(min_value = 0)
  
class CPLSubmissionResponseSerializer(CPLSubmissionDataSerializer):
  base_rating_classes = ContractorBaseRateSerializer(many = True)
  manual_rate = CPLManualRateResponseSerializer()
  sub_type = serializers.CharField() #May need to refactor this, how to handle sub types?

#Professional Response Serializers  
class ProfessionalBaseRateSerializer(ProfessionalBaseRatingClassDataSerializer):
  premium = serializers.IntegerField(min_value = 0)
  

  
class ContractorClassSerializer(serializers.HyperlinkedModelSerializer):
  class Meta:
    model = ContractorClass
    fields = ( 'iso_code', 'iso_description')
    
class ProfessionalClassSerializer(serializers.HyperlinkedModelSerializer):
  class Meta:
    model = ProfessionalClass
    fields = ( 'iso_code', 'iso_description')