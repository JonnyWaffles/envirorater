from rest_framework import serializers
from .models import ContractorClass


# Need to create Submission Serializers and Submission Response Serializers
#Submission Serializers
class ContractorSubmissionDataSerializer(serializers.Serializer):
  iso_code = serializers.IntegerField(min_value = 0)
  revenue = serializers.IntegerField(min_value = 0)
  mold_hazard_group = serializers.CharField()
  
class ManualRateDataSerializer(serializers.Serializer):
  limits = serializers.IntegerField(min_value = 0)
  deductible = serializers.IntegerField(min_value = 0)
  primary_nose_coverage = serializers.IntegerField(min_value = 0)
  mold_nose_coverage = serializers.IntegerField(min_value = 0)

class SubmissionDataSerializer(serializers.Serializer):
  contractor_classes = ContractorSubmissionDataSerializer(many = True)
  manual_rate = ManualRateDataSerializer() 
  
  
#Response Serializers  
class ContractorBaseRateSerializer(serializers.Serializer):
  iso_code = serializers.IntegerField(min_value = 0)
  premium_ex_mold = serializers.IntegerField(min_value = 0)
  mold_premium = serializers.IntegerField(min_value = 0)
  premium = serializers.IntegerField(min_value = 0)
  
class SubmissionResponseSerializer(serializers.Serializer):
  sub_type = serializers.CharField()
  contractor_classes = ContractorBaseRateSerializer(many = True)
  manual_rate = ManualRateDataSerializer()   
  
class ContractorClassSerializer(serializers.HyperlinkedModelSerializer):
  class Meta:
    model = ContractorClass
    fields = ( 'iso_code', 'iso_description')