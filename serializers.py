from rest_framework import serializers
from .models import (ContractorClass, ProfessionalClass, CPLSubmissionBaseRate, ProfessionalSubmissionBaseRate,
                     CPLSubmissionManualRate, ProfessionalSubmissionManualRate, CPLSubmission, ProfessionalSubmission,
                     SubmissionSet)



class ContractorClassSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ContractorClass
        fields = ( 'iso_code', 'iso_description')
    
class ProfessionalClassSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfessionalClass
        fields = ( 'iso_code', 'iso_description')


#Note we use the PremiumModifierAPISerializer for both requests and responses by changing the _premium field.
class PremiumModifierAPISerializer(serializers.Serializer):
    choices = ['limit1', 'limit2', 'deductible', 'primary_nose_coverage', 'mold_nose_coverage','aggregate_deductible_multiplier', 'prior_acts_years']
  
    premium = serializers.IntegerField(min_value = 0)
    modifier = serializers.ChoiceField(choices)
    mod_value = serializers.CharField()