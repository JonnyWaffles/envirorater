from django.contrib.auth.models import User
from rest_framework import serializers
from .models import (ContractorClass, ProfessionalClass, CPLSubmissionBaseRate, ProfessionalSubmissionBaseRate,
                     CPLSubmissionManualRate, ProfessionalSubmissionManualRate, CPLSubmission, ProfessionalSubmission,
                     SubmissionSet)

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')

class ContractorClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContractorClass
        fields = ( 'iso_code', 'iso_description')
        #Note need to set up a 'contractor_class-detail' view name which receives
        #iso_code rather than PK
        
    
class ProfessionalClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalClass
        fields = ( 'iso_code', 'iso_description')
        extra_kwargs = {
            'url' : {'view_name' : 'contractor_class-detail', 'lookup_field' : 'iso_code'},
        }
        
class CPLSubmissionBaseRateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CPLSubmissionBaseRate
        exclude = ('iso_factor', 'revenue_band_factor', 'mold_hazard_factor', 'submission')
        read_only_fields = ('premium', 'mold_premium', 'premium_ex_mold')        
        
class ProfessionalSubmissionBaseRateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfessionalSubmissionBaseRate
        exclude = ('iso_factor', 'revenue_band_factor', 'submission')
        read_only_fields = ('premium', )
        
class CPLSubmissionManualRateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CPLSubmissionManualRate
        exclude = ('limit_factor', 'deductible_factor',
                   'primary_nose_coverage_factor', 'mold_nose_coverage_factor', 'submission')
        read_only_fields = ('total_premium', )
        
class ProfessionalSubmissionManualRateSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfessionalSubmissionManualRate
        exclude = ('limit_factor', 'deductible_factor', 'aggregate_deductible_multiplier_factor',
                   'state_factor', 'prior_acts_years_factor', 'submission')
        read_only_fields = ('total_premium', )
        
class CPLSubmissionSerializer(serializers.HyperlinkedModelSerializer):
    base_rating_classes = CPLSubmissionBaseRateSerializer(many = True)
    manual_rate = CPLSubmissionManualRateSerializer(required = False)
    #Note may also need to include a reference to submission_set here. Not sure yet.
    
    class Meta:
        model = CPLSubmission
        fields = '__all__'  
        
        
class ProfessionalSubmissionSerializer(serializers.HyperlinkedModelSerializer):
    base_rating_classes = ProfessionalSubmissionBaseRateSerializer(many = True)
    manual_rate = ProfessionalSubmissionManualRateSerializer(required = False)
    #Note may also need to include a reference to submission_set here. Not sure yet.
    
    class Meta:
        model = ProfessionalSubmission
        fields = '__all__'  
        
class SubmissionSetSerializer(serializers.HyperlinkedModelSerializer):
    cpl_submission = CPLSubmissionSerializer(required = False)
    professional_submission = ProfessionalSubmissionSerializer(required = False)
    owner = UserSerializer
    
    class Meta:
        model = SubmissionSet
        fields = '__all__'  
        
#Note we use the PremiumModifierAPISerializer for both requests and responses by changing the _premium field.
class PremiumModifierAPISerializer(serializers.Serializer):
    choices = ['limit1', 'limit2', 'deductible', 'primary_nose_coverage', 'mold_nose_coverage','aggregate_deductible_multiplier', 'prior_acts_years']
  
    premium = serializers.IntegerField(min_value = 0)
    modifier = serializers.ChoiceField(choices)
    mod_value = serializers.CharField()