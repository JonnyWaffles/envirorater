from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.exceptions import APIException, ValidationError
from .models import (ContractorClass, ProfessionalClass, CPLSubmissionBaseRate, ProfessionalSubmissionBaseRate,
                     CPLSubmissionManualRate, ProfessionalSubmissionManualRate, CPLSubmission, ProfessionalSubmission,
                     SubmissionSet, Submission, SubmissionManualRate, Limit, ContractorsPollutionRevenueBand, ProfessionalRevenueBand,
                     Deductible, Nose, Aggregate, PriorActs, State
                     )
from rest_framework_bulk import (BulkSerializerMixin, BulkListSerializer,)

#Helper function to update each Submission instance with the validated base_rating_classes data. 
#requires data to be validated before called.
def update_or_create_submissions_base_rating_units(base_rating_classes_data, submission_instance, raw = False):
                
    assert isinstance(submission_instance, Submission), (
        'Exepected Submission instance, received %s instance.' %
        (submission_instance.__class__.__name__)
        )
    base_rating_classes = submission_instance.base_rating_classes

    for unit_data in base_rating_classes_data:
        unit_iso_code = unit_data.pop('iso_code')
        #Get the BaseRate instance and update the data, use the instance's attribute as the default.
        try:
            unit = base_rating_classes.get(iso_code = unit_iso_code)
            for key in unit_data.keys():
                attr = unit_data.pop(key, getattr(unit, key))
                setattr(unit, key, attr[key])
           
          
        #If an instance matching the iso_code cannot be found, create a new one using the data.
        except ObjectDoesNotExist:
            unit = submission_instance.base_rating_classes.create(iso_code = unit_iso_code, **unit_data)
         #If raw just save the provided values perform no calculations or look ups
        if raw:
            unit.save()
        else:
            unit.update_all_premiums()
            unit.save()

    submission_instance.save()

    return submission_instance

#Helper function to update each Submission instance with the validated manual_rate data.
#Requires data to be validated before called.
def update_or_create_submissions_manual_rate(manual_rate_data, submission_instance, raw = False):

    assert isinstance(submission_instance, Submission), (
                    'Exepected Submission instance, received %s instance.' %
                    (submission_instance.__class__.__name__)
                    )
    try:
        submission_instance.manual_rate
        manual_rate = submission_instance.manual_rate
        for key in manual_rate_data.keys():
            attr = manual_rate_data.pop(key, getattr(manual_rate, key))
            setattr(manual_rate, key, attr[key])
    except ObjectDoesNotExist:
        #There has to be a better way to set which ManualRate class is used here
        #Originally I tried submission_instance.manual_rate.create(**manual_rate_data)
        #But you cannot use the related name 'manual_rate' to instantiate itself, as
        #The object does not exist yet to call the create on.
        #But in the name of time we'll just perform a hard check.
        if isinstance(submission_instance, CPLSubmission):
            manual_rate = CPLSubmissionManualRate.objects.create(submission = submission_instance, **manual_rate_data)
        elif isinstance(submission_instance, ProfessionalSubmission):
            manual_rate = ProfessionalSubmissionManualRate.objects.create(submission = submission_instance, **manual_rate_data)
        else:
            raise ValueError('Unrecognized submission_type %s' % (submission_instance.__class__.__name__))

    if raw:
        manual_rate.save()
    else:
        manual_rate.set_factor_values()
        manual_rate.save()

    submission_instance.save()
    return submission_instance  

#Helper function to update or create Submission instance with the validated submission data.
#Requires data to be validated before called. If no submission_instance is provided a
#submission_set_instance and submission_type must be provided to create a new submission_instance.
def update_or_create_submission(submission_data, submission_instance = None, submission_set_instance = None, submission_type = None, raw = False):

    if submission_instance:
        assert isinstance(submission_instance, Submission), (
            'Expected Submission instance, received %s instance.' %
            (submission_instance.__class__.__name__)
            )
    
    if submission_set_instance:
        assert isinstance(submission_set_instance, SubmissionSet), (
            'Expected submission_set to be a SubmissionSet instance, received %s.' %
            (submission_set_instance.__class__.__name__)
            )

    if submission_type:
        assert issubclass(submission_type, Submission), (
            'Expected Submission subclass as a submission_type, received %s class.' %
            (submission_type.__class__.__bases__)
            )

    if not submission_instance and not submission_type:
        raise ValueError('No submission instance was provided, therefore'
                         'a submission_type and submission_set must be provided.')

    

    if not submission_instance and submission_type and not submission_set_instance:
        raise ValueError('No submission instance was provided, therefore'
                         'a submission_type and submission_set must be provided.')

    if not submission_instance:
        submission_instance = submission_type.objects.create(submission_set = submission_set_instance)

    base_rating_classes_data = submission_data.pop('base_rating_classes', None)
    manual_rate_data = submission_data.pop('manual_rate', None)

    if base_rating_classes_data:
        update_or_create_submissions_base_rating_units(base_rating_classes_data, submission_instance, raw)
    if manual_rate_data:
        update_or_create_submissions_manual_rate(manual_rate_data, submission_instance, raw)

    if not raw: 
        submission_instance.get_manual_rate_total()
    submission_instance.save()
    return submission_instance

class AdminOnlyFactorFieldMixin(object):
    admin_only_fields = ('factor', 'cumulative_premium')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs['context'].get('request', None)
        if not request.user.is_staff:
            field_names = self.fields.keys()
            factor_fields = [field for field in field_names if field in self.admin_only_fields]
            for name in factor_fields:
                self.fields.pop(name)
    

class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff')
        
class ContractorClassSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    
    class Meta:
        model = ContractorClass
        fields = ('url', 'iso_code', 'iso_description', 'factor')
        extra_kwargs = {
            'url' : { 'lookup_field' : 'iso_code'}
        }
        
class ProfessionalClassSerializer(AdminOnlyFactorFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = ProfessionalClass
        fields = ( 'iso_code', 'iso_description', 'factor' ,'url')
        extra_kwargs = {
            'url' : {'lookup_field' : 'iso_code'},
        }
        
class ProfessionalRevenueBandSerializer(AdminOnlyFactorFieldMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ProfessionalRevenueBand
        fields = '__all__'

class ContractorsPollutionRevenueBandSerializer(AdminOnlyFactorFieldMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ContractorsPollutionRevenueBand
        fields = '__all__'

class DeductibleSerializer(AdminOnlyFactorFieldMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Deductible
        fields = '__all__'

class LimitSerializer(AdminOnlyFactorFieldMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Limit
        fields = '__all__'

class PriorActsSerializer(AdminOnlyFactorFieldMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PriorActs
        fields = '__all__'

class AggregateSerializer(AdminOnlyFactorFieldMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Aggregate
        fields = '__all__'

class StateSerializer(AdminOnlyFactorFieldMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = State
        fields = '__all__'

class NoseSerializer(AdminOnlyFactorFieldMixin, serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Nose
        fields = '__all__'
    
class BaseRateSerializerMixin(object):
    """
    Create or update BaseRate Model Instance
    """
    def get_url(self, instance):
        return instance.get_absolute_url(self.context['request'])

    def create(self, validated_data):
        #In the view's perform_create method the submission is set as a kwarg when saving.
        #The save method merges all the kwargs with the validated_data
        submission = validated_data.pop('submission')
        raw = validated_data.pop('raw', False)
        
        instance = update_or_create_submissions_base_rating_units(validated_data, submission, raw)

        instance.save()

        return instance

    def update(self, instance, validated_data):
        raw = validated_data.pop('raw', False)        
        for key in validated_data:
                attr = validated_data.get(key, getattr(instance, key))
                setattr(instance, key, attr)
        if not raw:
            instance.update_all_premiums()
        instance.save()

        return instance

class ManualRateSerializerMixin(object):
    """
    Create or update a ManualRate Model Instance
    """
    #def get_url(self, instance):
    #    return instance.get_absolute_url(self.context['request'])

    def create(self, validated_data):
        submission = validated_data.pop('submission')
        raw = validated_data.pop('raw', False)

        instance = update_or_create_submissions_manual_rate(validated_data, submission, raw)

        instance.save()

        return instance

    def update(self, instance, validated_data):
        raw = validated_data.pop('raw', False)
        instance = update_or_create_submissions_manual_rate(validated_data, instance.submission, raw)

        instance.save()

        return instance

class SubmissionSerializerMixin(object):
    def get_url(self, instance):
        return instance.get_absolute_url(self.context['request'])

    def create(self, validated_data):
        submission_set = validated_data.pop('submission_set')
        raw = validated_data.pop('raw')

        instance = update_or_create_submission(validated_data, submission_set_instance = submission_set,
                                               submission_type = self.Meta.model, raw = raw)

        instance.save()

        return instance

    def update(self, instance, validated_data):
        raw = validated_data.pop('raw')
        update_or_create_submission(validated_data, instance, raw = raw)

        instance.save()

        return instance

class SubmissionSetSerializerMixin(object):

    def create(self, validated_data):
        
        #If performing a raw save without evaluation, such as for historical submission data, 
        #use the data's owner otherwise owner will be set by the view.
        raw = validated_data.get("raw", False)

        instance = SubmissionSet.objects.create(owner = validated_data.get("owner"))

        if 'cpl_submission' in validated_data.keys():
            cpl_submission_data = validated_data.pop('cpl_submission')
            instance.cpl_submission = update_or_create_submission(
                cpl_submission_data, submission_set_instance = instance,
                submission_type = CPLSubmission,  raw = raw)
            
        if 'professional_submission' in validated_data.keys():
            professional_submission_data = validated_data.pop('professional_submission')
            instance.professional_submission = update_or_create_submission(
                professional_submission_data, submission_set_instance = instance,
                submission_type = ProfessionalSubmission, raw = raw)     
            
        instance.save()
            
        return instance
    
    def update(self, instance, validated_data):
        
        raw = validated_data.get("raw", False)
        
        if 'cpl_submission' in validated_data.keys():
            cpl_submission_data = validated_data.pop('cpl_submission')
            update_or_create_submission(cpl_submission_data,
                                        submission_instance = instance.cpl_submission,
                                        raw = raw)
            
        if 'professional_submission' in validated_data.keys():
            professional_submission_data = validated_data.pop('professional_submission')
            update_or_create_submission(professional_submission_data,
                                        submission_instance = instance.professional_submission,
                                        raw = raw)

        instance.save()

        return instance
        
class CPLSubmissionBaseRateSerializer(BaseRateSerializerMixin, serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = CPLSubmissionBaseRate
        exclude = ('iso_factor', 'revenue_band_factor', 'mold_hazard_factor', 'submission', 'id')
        read_only_fields = ('premium', 'mold_premium', 'premium_ex_mold')
        
class ProfessionalSubmissionBaseRateSerializer(BaseRateSerializerMixin, serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = ProfessionalSubmissionBaseRate
        exclude = ('iso_factor', 'revenue_band_factor', 'submission', 'id')
        read_only_fields = ('premium', )
        
class CPLSubmissionManualRateSerializer(ManualRateSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = CPLSubmissionManualRate
        exclude = ('limit_factor', 'deductible_factor', 'id',
                   'primary_nose_coverage_factor', 'mold_nose_coverage_factor', 'submission')
        read_only_fields = ('total_premium', )

class ProfessionalSubmissionManualRateSerializer(ManualRateSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = ProfessionalSubmissionManualRate
        exclude = ('limit_factor', 'deductible_factor', 'aggregate_deductible_multiplier_factor',
                   'state_factor', 'prior_acts_years_factor', 'submission', 'id')
        read_only_fields = ('total_premium', )
        
class CPLSubmissionSerializer(SubmissionSerializerMixin, serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    base_rating_classes = CPLSubmissionBaseRateSerializer(many = True)
    manual_rate = CPLSubmissionManualRateSerializer(required = False)
    
    class Meta:
        model = CPLSubmission
        exclude = ('id',  )       
        
class ProfessionalSubmissionSerializer(SubmissionSerializerMixin, serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    base_rating_classes = ProfessionalSubmissionBaseRateSerializer(many = True)
    manual_rate = ProfessionalSubmissionManualRateSerializer(required = False)    
    
    class Meta:
        model = ProfessionalSubmission
        exclude = ('id', )

class SubmissionSetSerializer(SubmissionSetSerializerMixin, serializers.ModelSerializer):
    insured_name = serializers.CharField(required = False)
    url = serializers.HyperlinkedIdentityField(view_name='submissions-detail')
    cpl_submission = CPLSubmissionSerializer(required = False)
    professional_submission = ProfessionalSubmissionSerializer(required = False)
    owner = UserSerializer(read_only = True)    

    class Meta:
        model = SubmissionSet
        fields = '__all__'
        
#Note we use the PremiumModifierAPISerializer for both requests and responses by changing the _premium field.
class PremiumModifierAPISerializer(serializers.Serializer):
  
    premium = serializers.IntegerField(min_value = 0)
    limit = serializers.CharField(required = False)
    deductible = serializers.IntegerField(min_value = 0, required = False)
    primary_nose_coverage = serializers.IntegerField(min_value = 0, required = False)
    mold_nose_coverage = serializers.IntegerField(min_value = 0, required = False)
    aggregate_deductible_multiplier = serializers.IntegerField(min_value = 0, required = False)
    prior_acts_years = serializers.IntegerField(min_value = 0, required = False)
    state = serializers.CharField(required = False)

    def mod_premium(self):
        validated_data = self.validated_data
        premium = validated_data.pop('premium')
        factor_dict = {}
        #Once again limits are a special case.  We need the user to input them
        #'limit1/limit2'.      
        if 'limit' in validated_data:
            try:
                data_string = validated_data.pop('limit')
                limit1 = data_string.split('/')[0]
                limit2 = data_string.split('/')[1]
            except:
                raise ValidationError('Limits must be separated by a slash. Ex. 10000/5000')
            try:
                limit = Limit.objects.get(limit1__iexact = limit1, limit2__iexact = limit2)
                factor_dict.update({'limit1' : limit2, 'limit2' : limit2})
            except ObjectDoesNotExist:
                raise ValidationError('That limit object could not be found')					
        for factor in validated_data:
            factor_dict.update({factor : validated_data.get(factor)})
        premium = SubmissionManualRate.mod_premium(premium, factor_dictionary = factor_dict)
        return({'modded_premium' : premium })