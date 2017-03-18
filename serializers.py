from rest_framework import serializers
from .models import ContractorClass
from .views import ContractorBaseRate, Submission

class ContractorBaseRateSerializer(serializers.Serializer):
  iso_code = serializers.IntegerField()
  premium_ex_mold = serializers.DecimalField(max_digits=19, decimal_places=2)
  mold_premium = serializers.DecimalField(max_digits=19, decimal_places=2)
  premium = serializers.DecimalField(max_digits=19, decimal_places=2)
  
class ManualRateSerializer(serializers.Serializer):
  limits = serializers.IntegerField()
  deductible = serializers.IntegerField()
  primary_nose_coverage = serializers.IntegerField()
  mold_nose_coverage = serializers.IntegerField()
  
class SubmissionSerializer(serializers.Serializer):
  sub_type = serializers.CharField()
  contractor_classes = ContractorBaseRateSerializer(many = True)
  manual_rate = ManualRateSerializer()    
  
class ContractorClassSerializer(serializers.HyperlinkedModelSerializer):
  class Meta:
    model = ContractorClass
    fields = ( 'iso_code', 'iso_description')