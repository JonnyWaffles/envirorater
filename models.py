from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.utils import timezone
from rest_framework.reverse import reverse
from decimal import Decimal
# Create your models here.

#These are look up tables. We don't want to save references to the look up tables in the object model,
#Because the factors could change. We need to save the historical data.
class FactorLookUpTable(models.Model):
    #An abstract parent class for all look up models with factor values
    factor = models.DecimalField(max_digits = 3, decimal_places = 2)

    def return_factor(self):
        return self.factor

    class Meta:
        abstract = True

class BaseRatingUnit(models.Model):

    iso_code = models.PositiveIntegerField(primary_key = True)  
    iso_description = models.CharField(max_length = 140)
    #Using 'factor' over class_relativity' for consistency

    def __str__(self):
        return "ISO Code: %s Description: %s" % (self.iso_code, self.iso_description)

    class Meta:
        abstract = True

class ContractorClass(BaseRatingUnit, FactorLookUpTable):
    
    def get_premium_ex_mold(self, revenue = 0):
        
        revenue_band = ContractorsPollutionRevenueBand.objects.get(start__lt = revenue, end__gte = revenue)
        marginal_premium = (revenue - revenue_band.start) * revenue_band.factor / 1000
        class_premium_ex_mold = (revenue_band.cumulative_premium + marginal_premium) * self.factor
        return class_premium_ex_mold
  
    def get_mold_premium(self, revenue = 0, mold_hazard_group = "low"):
        revenue_band = ContractorsPollutionRevenueBand.objects.get(start__lt = revenue, end__gte = revenue)
        class_premium_ex_mold = ContractorClass.get_premium_ex_mold(self, revenue)
        mold_hazard_group = MoldHazardGroup.objects.get(mold_hazard_group__iexact = mold_hazard_group)
        return class_premium_ex_mold * mold_hazard_group.factor
  
    def get_total_premium(self, revenue = 0, mold_hazard_group = "low"):
        return ContractorClass.get_premium_ex_mold(self, revenue) + ContractorClass.get_mold_premium(self, revenue, mold_hazard_group)

class ProfessionalClass(BaseRatingUnit, FactorLookUpTable):
  
    def get_premium(self, revenue = 0):
        revenue_band = ProfessionalRevenueBand.objects.get(start__lt = revenue, end__gte = revenue)
        marginal_premium = (revenue - revenue_band.start) * revenue_band.factor / 1000
        premium = (revenue_band.cumulative_premium + marginal_premium) * self.factor
        return premium

class RevenueBand(models.Model):

    start = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    cumulative_premium = models.PositiveIntegerField()

    def __str__(self):
        return "%s - %s Factor: %s" % (self.start, self.end, self.factor)

    class Meta:
        abstract = True

class ContractorsPollutionRevenueBand(RevenueBand, FactorLookUpTable):
    pass
    
class ProfessionalRevenueBand(RevenueBand, FactorLookUpTable):
    pass

class MoldHazardGroup(FactorLookUpTable):

    mold_hazard_group = models.CharField(max_length = 20)
  
    def __str__(self):
        return "Group: %s - Factor: %s" % (self.mold_hazard_group, self.factor)

class Limit(FactorLookUpTable):

    limit1 = models.PositiveIntegerField(default = 1000000)
    limit2 = models.PositiveIntegerField(default = 1000000) 
    minimum_premium = models.PositiveIntegerField(default = 500)
  
    def __str__(self):
        return "%s/%s" % (self.limit1, self.limit2)

class Deductible(FactorLookUpTable):

    deductible = models.PositiveIntegerField()
  
    def __str__(self):
        return "%s" % (self.deductible)

class Aggregate(FactorLookUpTable):

    aggregate_deductible_multiplier = models.PositiveIntegerField()

class Nose(FactorLookUpTable):

    primary_nose_coverage = models.PositiveIntegerField()
    mold_nose_coverage = models.PositiveIntegerField()
    years = models.PositiveIntegerField()
  
    def __str__(self):
        return "%s" % (self.years)

class PriorActs(FactorLookUpTable):

    prior_acts_years = models.CharField(max_length = 10)
  
    def __str__(self):
        return "Years: %s" % (self.prior_acts_years)

class State(FactorLookUpTable):

    state = models.CharField(max_length = 20)
    
    def __str__(self):
        return "State: %s" % (self.state)

#Saving ratings
#You don't want the saved models to reference the look up tables in case the look up tables change.
#Save "values" only!

#Note model is abstract, instances need to set a submission = foreignkey to sub model relatonship.
class SubmissionBaseRate(models.Model):
    #Override this value in child classes
    base_rate_class = None
    revenue_class = None
    
    iso_code = models.PositiveIntegerField()  
    iso_description = models.CharField(max_length = 140, blank = True, null = True)
    iso_factor = models.DecimalField(max_digits = 3, decimal_places = 2, default = 1, blank = True)
    revenue = models.PositiveIntegerField(default = 0)
    revenue_band_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1, blank = True)
    premium = models.PositiveIntegerField(default = 0, blank = True) 
    
    def get_base_rate_object(self):
        base_rate_object = self.base_rate_class.objects.get(iso_code__iexact = self.iso_code)
        return base_rate_object
    
    def get_revenue_band_object(self):
        revenue_band_object = self.revenue_class.objects.get(start__lt = self.revenue, end__gte = self.revenue)
        return revenue_band_object
    
    def get_iso_description(self):
        return self.get_base_rate_object().iso_description
    
    def get_iso_factor(self):
        return self.get_base_rate_object().factor
    
    def get_revenue_band_factor(self):
        return self.get_revenue_band_object().factor

    def update_all_premiums(self):
        raise NotImplementedError

    def __str__(self):
        return ("iso_code: %s submission: %s premium: %s" %
                (self.iso_code, self.submission, self.premium))

    class Meta:
        abstract = True
        unique_together = ('submission', 'iso_code',)
        

class SubmissionManualRate(models.Model):

    limit1 = models.PositiveIntegerField(default = 1000000)
    limit2 = models.PositiveIntegerField(default = 1000000)
    limit_factor = models.DecimalField(max_digits = 3, decimal_places = 2, default = 1, blank = True)
    deductible = models.PositiveIntegerField(default = 10000)
    deductible_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1, blank = True)
    total_premium = models.PositiveIntegerField(default = 0, blank = True)
    
    #Register the factors and their respective Lookup Class here.
    factor_types = {'deductible' : Deductible, 'primary_nose_coverage' : Nose, 'mold_hazard_group' : MoldHazardGroup,
                    'mold_nose_coverage' : Nose, 'aggregate_deductible_multiplier' : Aggregate, 'state' : State,
                    'prior_acts_years' : PriorActs, 'limit1' : Limit, 'limit2' : Limit}

    @classmethod
    def register_factor_type(cls, factor_type):
        for factor_name, factor_class in factor_type.items():
            if isinstance(factor_name[factor_class], FactorLookUpTable):
                cls.factor_types.update(factor_type)
            else:
                raise TypeError("Only FactorLookupTables can be registered as factor_types")

    #This helper function accepts a dictionary of factor look up value arguments and returns a dictionary of 
    #type_factor : factor_value items. So if {'deductible' : 10000} is provided {'deductible_factor' : 1} returns.
    @staticmethod
    def get_factor_values(factor_dictionary):

        factor_value_dict = {}

        #Limit factor is a special case because it needs two values from the
        #calling object
        if 'limit1' in factor_dictionary.keys() and 'limit2' in factor_dictionary.keys():
            limit = Limit.objects.get(limit1__iexact = factor_dictionary['limit1'],
                                        limit2__iexact = factor_dictionary['limit2'])
            factor_value_dict.update( {'limit_factor' : limit.factor} )
            #Remove the limits once we're done with them from the list so 
            #they do not trigger twice.
            factor_dictionary.pop('limit1')
            factor_dictionary.pop('limit2')

        for factor in factor_dictionary:
            #Check to make sure the factor requested is an allowed factor type.            
            if factor in SubmissionManualRate.factor_types.keys():
                
                query = {'{0}__iexact'.format(factor) : factor_dictionary[factor]}
                factor_lookup_table = SubmissionManualRate.factor_types[factor].objects.get(**query)
                factor_value_dict.update( {'{0}_factor'.format(factor) : factor_lookup_table.factor} )
        return factor_value_dict
    
    #This helper function returns a dictionary of a ManualRate instance's factor attributes and their values
    #So we can look up the values with get_factor_values()
    def get_factor_attributes(self):
        repr(self)
        factor_dictionary = {}
        #We only want factor attributes
        factor_list = dir(self)
        for attr in factor_list:
            if attr in SubmissionManualRate.factor_types.keys():
                factor_dictionary.update({attr : getattr(self, attr)})
        return factor_dictionary

    #This function sets the instances factor_type attributes using its factor values
    def set_factor_values(self):
        factor_dict = self.get_factor_attributes()
        factor_value_dict = self.get_factor_values(factor_dict)
        for k, v in factor_value_dict.items():
            setattr(self, k, v)      
    
    #This static method takes either a manual_rate instance or a factor_dictionary and returns a premium.
    @staticmethod
    def mod_premium(premium = 0, manual_rate = None, factor_dictionary = None):
        if not manual_rate and not factor_dictionary:
            raise ValueError("Mod premium requires a manual_rate instances or a factor_dictionary")

        if manual_rate and factor_dictionary:
            raise ValueError("Both a manual_rate instance and a factor_dictionary provided. Use one, not both.")

        if manual_rate:
            assert isinstance(manual_rate, SubmissionManualRate), "manual_rate must be a ManualRate instance."
            factor_dictionary = manual_rate.get_factor_attributes()

        factor_value_dict = SubmissionManualRate.get_factor_values(factor_dictionary)
        for factor in factor_value_dict.values():
            premium *= factor
        return premium
    
    def __str__(self):
        return ("%s submission: %s total_premium: %s" % 
                (self.__class__.__name__, self.submission, self.total_premium))
   
    class Meta:
        abstract = True
        
class CPLSubmissionBaseRate(SubmissionBaseRate):
    #Set the appropriate classes
    base_rate_class = ContractorClass
    revenue_class = ContractorsPollutionRevenueBand
    
    mold_hazard_group = models.CharField(max_length = 20, default = "Low", blank = True)
    mold_hazard_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 0.050, blank = True) 
    premium_ex_mold = models.PositiveIntegerField(default = 0, blank = True)
    mold_premium = models.PositiveIntegerField(default = 0, blank = True)
    submission = models.ForeignKey('CPLSubmission', on_delete = models.CASCADE, related_name = 'base_rating_classes')
    
    def get_mold_hazard_factor(self):
        mold_hazard_group = MoldHazardGroup.objects.get(mold_hazard_group__iexact = self.mold_hazard_group)
        return mold_hazard_group.factor
    
    def get_premium_ex_mold(self):
        base_rate_object = self.get_base_rate_object()
        premium_ex_mold = base_rate_object.get_premium_ex_mold(self.revenue)
        return premium_ex_mold
    
    def get_mold_premium(self):
        base_rate_object = self.get_base_rate_object()
        mold_premium = base_rate_object.get_mold_premium(self.revenue)
        return mold_premium

    def get_total_premium(self):
        base_rate_object = self.get_base_rate_object()
        total_premium = base_rate_object.get_total_premium(self.revenue)
        return total_premium
    
    def update_all_premiums(self):
        self.premium_ex_mold = self.get_premium_ex_mold()
        self.mold_premium = self.get_mold_premium()
        self.premium = self.get_total_premium()
        self.mold_hazard_factor = self.get_mold_hazard_factor()
        self.iso_description = self.get_iso_description()
        self.iso_factor = self.get_iso_factor()
        self.revenue_band_factor = self.get_revenue_band_factor()

    def get_absolute_url(self, request = None):
        set_id = self.submission.submission_set.id
        return reverse('cpl-units-detail', kwargs={'submission_set' : set_id, 'iso_code' : self.iso_code},
                       request = request)
    
class ProfessionalSubmissionBaseRate(SubmissionBaseRate):

    base_rate_class = ProfessionalClass
    revenue_class = ProfessionalRevenueBand
    
    submission = models.ForeignKey('ProfessionalSubmission', on_delete = models.CASCADE, related_name = 'base_rating_classes')

    def update_all_premiums(self):
        self.iso_description = self.get_iso_description()
        self.iso_factor = self.get_iso_factor()
        self.revenue_band_factor = self.get_revenue_band_factor()
        self.premium = self.get_base_rate_object().get_premium(self.revenue)

    def get_absolute_url(self, request = None):
        set_id = self.submission.submission_set.id
        return reverse('pro-units-detail', kwargs={'submission_set' : set_id, 'iso_code' : self.iso_code},
                       request = request)
    
class CPLSubmissionManualRate(SubmissionManualRate):

    primary_nose_coverage = models.PositiveIntegerField(default = 0, blank = True)
    primary_nose_coverage_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1, blank = True)
    mold_nose_coverage = models.PositiveIntegerField(default = 0, blank = True)
    mold_nose_coverage_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1, blank = True)
    submission = models.OneToOneField('CPLSubmission', on_delete = models.CASCADE, related_name = 'manual_rate')
    
    def get_absolute_url(self, request = None):
        set_id = self.submission.submission_set.id
        return reverse('cpl-manual-rate-detail', kwargs={'submission_set' : set_id},
                       request = request)
    
class ProfessionalSubmissionManualRate(SubmissionManualRate):

    aggregate_deductible_multiplier = models.PositiveIntegerField(default = 1, blank = True)
    aggregate_deductible_multiplier_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1.000, blank = True)
    state = models.CharField(max_length = 20, default = 'Virginia', blank = True)
    state_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1.000, blank = True)
    prior_acts_years = models.CharField(max_length = 10, default = 'Full', blank = True)
    prior_acts_years_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1.000, blank = True)
    submission = models.OneToOneField('ProfessionalSubmission', on_delete = models.CASCADE, related_name = 'manual_rate')
    
    def get_absolute_url(self, request = None):
        set_id = self.submission.submission_set.id
        return reverse('pro-manual-rate-detail', kwargs={'submission_set' : set_id},
                       request = request)

#Abstract class just to type the specific submissions as submissions
class Submission(models.Model):

    def __str__(self):
        return ("%s id: %s" % (self.__class__.__name__, self.id))

    class Meta:
        abstract = True
        
class CPLSubmission(Submission):

    def get_base_unit_totals(self):

        total_premium_ex_mold = 0
        total_mold_premium = 0
        
        for base_rating_unit in self.base_rating_classes.all():
            total_premium_ex_mold += base_rating_unit.premium_ex_mold
            total_mold_premium += base_rating_unit.mold_premium
            total_premium = total_premium_ex_mold + total_mold_premium

        totals_dict = {
            'total_premium_ex_mold' : total_premium_ex_mold,
            'total_mold_premium' : total_mold_premium,
            'total_premium' : total_premium
            }

        return totals_dict

    def get_manual_rate_total(self):
        totals_dict = self.get_base_unit_totals()
        for premium_type in totals_dict:
            manual_rate = self.manual_rate
            original_premium = totals_dict[premium_type]
            new_premium = SubmissionManualRate.mod_premium(original_premium, manual_rate)
            setattr(manual_rate, premium_type, new_premium)
            manual_rate.save()
    
    def get_absolute_url(self, request = None):
        set_id = self.submission_set.id
        return reverse('cpl-details', kwargs={'submission_set' : set_id}, request = request)

class ProfessionalSubmission(Submission):

    def get_base_unit_totals(self):

        total_premium = 0

        for base_rating_unit in self.base_rating_classes.all():
            total_premium += base_rating_unit.premium

        return total_premium

    def get_manual_rate_total(self):
        manual_rate = self.manual_rate
        total_premium = SubmissionManualRate.mod_premium(self.get_base_unit_totals(), manual_rate)
        setattr(manual_rate, 'total_premium', total_premium)
        manual_rate.save()
            
    def get_absolute_url(self, request = None):
        set_id = self.submission_set.id
        return reverse('pro-details', kwargs={'submission_set' : set_id}, request = request)
        
    

class SubmissionSet(models.Model):
    insured_name = models.CharField(max_length = 140, default = 'Default Named Insured', blank = True)
    cpl_submission = models.OneToOneField('CPLSubmission', on_delete = models.CASCADE, blank = True, null = True, related_name = 'submission_set')
    professional_submission = models.OneToOneField('ProfessionalSubmission', on_delete = models.CASCADE, blank = True, null = True, related_name = 'submission_set')
    bound = models.BooleanField(default = False, blank = True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null = True,
        blank = True
    )
    last_saved = models.DateField(auto_now = True)
    created_on = models.DateField(auto_now_add = True)

    def __str__(self):
        return ("insured_name: %s id: %s created_on: %s" %
                (self.insured_name, self.id, self.created_on))