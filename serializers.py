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
        fields = ( 'iso_code', 'iso_description', 'url')
        extra_kwargs = {
            'url' : { 'lookup_field' : 'iso_code'}
        }
    
class ProfessionalClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalClass
        fields = ( 'iso_code', 'iso_description', 'url')
        extra_kwargs = {
            'url' : {'lookup_field' : 'iso_code'},
        }
        
class CPLSubmissionBaseRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CPLSubmissionBaseRate
        exclude = ('iso_factor', 'revenue_band_factor', 'mold_hazard_factor', 'submission')
        read_only_fields = ('premium', 'mold_premium', 'premium_ex_mold')        
        
class ProfessionalSubmissionBaseRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalSubmissionBaseRate
        exclude = ('iso_factor', 'revenue_band_factor', 'submission')
        read_only_fields = ('premium', )
        
class CPLSubmissionManualRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CPLSubmissionManualRate
        exclude = ('limit_factor', 'deductible_factor',
                   'primary_nose_coverage_factor', 'mold_nose_coverage_factor', 'submission')
        read_only_fields = ('total_premium', )
        
class ProfessionalSubmissionManualRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfessionalSubmissionManualRate
        exclude = ('limit_factor', 'deductible_factor', 'aggregate_deductible_multiplier_factor',
                   'state_factor', 'prior_acts_years_factor', 'submission')
        read_only_fields = ('total_premium', )
        
class CPLSubmissionSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    base_rating_classes = CPLSubmissionBaseRateSerializer(many = True)
    manual_rate = CPLSubmissionManualRateSerializer(required = False)

    def get_url(self, instance):
        return instance.get_absolute_url(self.context['request'])
    
    class Meta:
        model = CPLSubmission
        exclude = ('id', )
        extra_kwargs = {
            'url' : { 'lookup_field' : 'iso_code'}
        }
        
        
class ProfessionalSubmissionSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    base_rating_classes = ProfessionalSubmissionBaseRateSerializer(many = True)
    manual_rate = ProfessionalSubmissionManualRateSerializer(required = False)
    
    def get_url(self, instance):
        return instance.get_absolute_url(self.context['request'])
    
    class Meta:
        model = ProfessionalSubmission
        exclude = ('id', )

class SubmissionSetSerializer(serializers.ModelSerializer):
    insured_name = serializers.CharField(required = False)
    url = serializers.HyperlinkedIdentityField(view_name='submissions-detail')
    cpl_submission = CPLSubmissionSerializer(required = False)
    professional_submission = ProfessionalSubmissionSerializer(required = False)
    owner = UserSerializer(read_only = True)   
    
    def create(self, validated_data, owner = None, *args, **kwargs):
        
        request = kwargs['context']['request']  
        raw = request.data.get('raw', False)
        submission_set = SubmissionSet.objects.create(owner = owner)
        
        
        if 'cpl_submission' in validated_data.keys():
            cpl_submission = CPLSubmission.objects.create()            
            for unit_data in validated_data['cpl_submission']['base_rating_classes']:
                unit = CPLSubmissionBaseRate(**unit_data)
                #Use the raw = True request keyword to keep the data from being recalculated
                if raw:
                    cpl_submission.base_rating_classes.add(unit, bulk = False)
                else:
                    unit.update_all_premiums()
                    cpl_submission.base_rating_classes.add(unit, bulk = False)
            submission_set.cpl_submission = cpl_submission
            
        if 'professional_submission' in validated_data.keys():
            professional_submission = ProfessionalSubmission.objects.create()
            for unit_data in validated_data['professional_submission']['base_rating_classes']:
                unit = ProfessionalSubmissionBaseRate(**unit_data)
                if raw:
                    professional_submission.base_rating_classes.add(unit, bulk = False)
                else:
                    unit.update_all_premiums()
                    professional_submission.base_rating_classes.add(unit, bulk = False)
            submission_set.professional_submission = professional_submission
            
        submission_set.save()
            
        return submission_set
    
    def update(self, instance, validated_data, *args, **kwargs):
        
        request = kwargs['context']['request']  
        raw = request.data.get('raw', False)
        
        instance.insured_name = validated_data.get('insured_name', instance.insured_name)
        instance.bound = validated_data.get('bound', instance.bound)
        
        if 'cpl_submission' in validated_data.keys():
            if instance.cpl_submission:
                cpl_submission = instance.cpl_submission
                
                 
    class Meta:
        model = SubmissionSet
        fields = '__all__'
        
#Note we use the PremiumModifierAPISerializer for both requests and responses by changing the _premium field.
class PremiumModifierAPISerializer(serializers.Serializer):
    choices = ['limit1', 'limit2', 'deductible', 'primary_nose_coverage', 'mold_nose_coverage','aggregate_deductible_multiplier', 'prior_acts_years']
  
    premium = serializers.IntegerField(min_value = 0)
    modifier = serializers.ChoiceField(choices)
    mod_value = serializers.CharField()