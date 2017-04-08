from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
# Create your models here.
#I should have made abstract base classes for BaseRateClass (ContractorClass and ProfessionalClass)
#and RevenueBand, but I don't want to have to rebuild those tables during testing...

#These are look up tables. We don't want to save references to the look up tables in the object model,
#Because they could change. We need to save the historical data.

class ContractorClass(models.Model):
    iso_code = models.PositiveIntegerField(primary_key = True)  
    iso_description = models.CharField(max_length = 140)
    #Renaming 'class_relativity' to 'factor' for consistency
    factor = models.DecimalField(max_digits = 3, decimal_places = 2)
  
    def __str__(self):
        return "ISO Code: %s Description: %s" % (self.iso_code, self.iso_description)
  #Can refactor this later since the only difference between this and the professional liability is
  #The mold premium
    def get_premium_ex_mold(self, revenue = 0):
        revenue_band = ContractorsPollutionRevenueBand.objects.get(start__lt = revenue, end__gte = revenue)
        marginal_premium = (revenue - revenue_band.start) * revenue_band.factor / 1000
        class_premium_ex_mold = (revenue_band.cumulative_premium + marginal_premium) * self.factor
        return class_premium_ex_mold
  
    def get_mold_premium(self, revenue = 0, mold_hazard_group = "low"):
        revenue_band = ContractorsPollutionRevenueBand.objects.get(start__lt = revenue, end__gte = revenue)
        class_premium_ex_mold = ContractorClass.get_premium_ex_mold(self, revenue)
        mold_hazard_group = MoldHazardGroup.objects.get(hazard_group__iexact = mold_hazard_group)
        return class_premium_ex_mold * mold_hazard_group.factor
  
    def get_total_premium(self, revenue = 0, mold_hazard_group = "low"):
        return ContractorClass.get_premium_ex_mold(self, revenue) + ContractorClass.get_mold_premium(self, revenue, mold_hazard_group)

class ProfessionalClass(models.Model):
    iso_code = models.PositiveIntegerField(primary_key = True)
    iso_description = models.CharField(max_length = 140)
    factor = models.DecimalField(max_digits = 3, decimal_places = 2)
  
    def __str__(self):
        return "ISO Code: %s Description: %s" % (self.iso_code, self.iso_description)
  
    def get_premium(self, revenue = 0):
        revenue_band = ProfessionalRevenueBand.objects.get(start__lt = revenue, end__gte = revenue)
        marginal_premium = (revenue - revenue_band.start) * revenue_band.factor / 1000
        premium = (revenue_band.cumulative_premium + marginal_premium) * self.factor
        return premium

class ContractorsPollutionRevenueBand(models.Model):
    start = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    cumulative_premium = models.PositiveIntegerField()
    factor = models.DecimalField(max_digits = 4, decimal_places = 3)
  
    def __str__(self):
        return "%s - %s Factor: %s" % (self.start, self.end, self.factor)
    
class ProfessionalRevenueBand(models.Model):
    start = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    cumulative_premium = models.PositiveIntegerField()
    factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1)
  
    def __str__(self):
        return "%s - %s Factor: %s" % (self.start, self.end, self.factor)

class MoldHazardGroup(models.Model):
    hazard_group = models.CharField(max_length = 20)
    factor = models.DecimalField(max_digits = 4, decimal_places = 3)
  
    def __str__(self):
        return "Group: %s - Factor: %s" % (self.hazard_group, self.factor)

class Limit(models.Model):
    limit1 = models.PositiveIntegerField(default = 1000000)
    limit2 = models.PositiveIntegerField(default = 1000000) 
    factor = models.DecimalField(max_digits = 4, decimal_places = 3)
    minimum_premium = models.PositiveIntegerField(default = 500)
  
    def __str__(self):
        return "%s/%s" % (self.limit1, self.limit2)

class Deductible(models.Model):
    deductible = models.PositiveIntegerField()
    factor = models.DecimalField(max_digits = 4, decimal_places = 3)
  
    def __str__(self):
        return "%s" % (self.deductible)

class Aggregate(models.Model):
    aggregate_deductible_multiplier = models.PositiveIntegerField()
    factor = models.DecimalField(max_digits = 4, decimal_places = 3)

class Nose(models.Model):
    primary_nose_coverage = models.PositiveIntegerField()
    mold_nose_coverage = models.PositiveIntegerField()
    years = models.PositiveIntegerField()
    factor = models.DecimalField(max_digits = 4, decimal_places = 3)
  
    def __str__(self):
        return "%s" % (self.years)

class PriorActs(models.Model):
    prior_acts_years = models.CharField(max_length = 10)
    factor = models.DecimalField(max_digits = 4, decimal_places = 3)
  
    def __str__(self):
        return "Years: %s" % (self.prior_acts_years)

class State(models.Model):
    state = models.CharField(max_length = 20)
    factor = models.DecimalField(max_digits = 4, decimal_places = 3)
    
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
    iso_description = models.CharField(max_length = 140, blank = True)
    iso_factor = models.DecimalField(max_digits = 3, decimal_places = 2, blank = True)
    revenue = models.PositiveIntegerField(default = 0)
    revenue_band_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1, blank = True)
    premium = models.PositiveIntegerField(default = 0, blank = True) 
    
    def get_iso_description(self):
        base_rate_object = self.base_rate_class.objects.get(iso_code__iexact = self.iso_code)
        return = self.base_rate_object.iso_description
    
    def get_iso_factor(self):
        base_rate_object = self.base_rate_class.objects.get(iso_code__iexact = self.iso_code)
        return self.base_rate_object.factor
    
    def get_revenue_band_factor(self):
        base_rate_object = self.revenue_class.objects.get(start__lt = revenue, end__gte = revenue)
        return = self.base_rate_object.factor
    
    def get_premium(self):
        return self.base_rate_class.get_premium(self.revenue)
        
    class Meta:
        abstract = True
        

class SubmissionManualRate(models.Model):
    limit1 = models.PositiveIntegerField(default = 1000000)
    limit2 = models.PositiveIntegerField(default = 1000000)
    limit_factor = models.DecimalField(max_digits = 3, decimal_places = 2, blank = True)
    deductible = models.PositiveIntegerField(default = 10000)
    deductible_factor = models.DecimalField(max_digits = 4, decimal_places = 3, blank = True)
    total_premium = models.PositiveIntegerField(default = 0, blank = True) 
    
    def get_limit_factor(self):
        limit = Limit.objects.get(limit1__iexact = factor_dict['limit1'], limit2__iexact = factor_dict['limit2']).factor
        return = limit.factor

    def get_deductible_factor(self):
        deductible = Deductible.objects.get(deductible__iexact = self.deductible)
        return = deductible.factor
        
    class Meta:
        abstract = True
        
class CPLSubmissionBaseRate(SubmissionBaseRate):
    base_rate_class = ContractorClass
    revenue_class = ContractorsPollutionRevenueBand    
    mold_hazard_group = models.CharField(max_length = 20, default = "Low", blank = True)
    mold_hazard_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 0.050, blank = True) 
    premium_ex_mold = models.PositiveIntegerField(default = 0, blank = True)
    mold_premium = models.PositiveIntegerField(default = 0, blank = True)
    submission = models.ForeignKey('CPLSubmission', on_delete = models.CASCADE, related_name = 'base_rating_classes')
    
    def get_mold_hazard_factor(self):
        mold_hazard_group = MoldHazardGroup.objects.get(hazard_group__iexact = self.mold_hazard_group)
        return mold_hazard_group.factor        
    
    def update_all_factors(self):
        self.iso_description = self.get_iso_description()
        self.iso_factor = self.get_iso_factor()
        self.revenue_band_factor = self.get_revenue_band_factor()
        self.mold_hazard_factor = self.get_mold_hazard_factor()
        
    def get_premium_ex_mold(self):
        return self.base_rate_class.get_premium_ex_mold(self.revenue)
    
    def get_mold_premium(self):
        return self.base_rate_class.get_mold_premium(self.revenue)
    
    def update_all_premiums(self):
        self.premium_ex_mold = self.get_premium_ex_mold()
        self.mold_premium = self.get_mold_premium()
        self.premium = self.get_premium()        
    
class ProfessionalSubmissionBaseRate(SubmissionBaseRate):
    base_rate_class = ProfessionalClass
    revenue_class = ProfessionalRevenueBand
    
    submission = models.ForeignKey('ProfessionalSubmission', on_delete = models.CASCADE, related_name = 'base_rating_classes')
    
    def update_all_premiums(self):
        self.premium = self.get_premium()
    
class CPLSubmissionManualRate(SubmissionManualRate):
    primary_nose_coverage = models.PositiveIntegerField(default = 0, blank = True)
    primary_nose_coverage_factor = models.DecimalField(max_digits = 4, decimal_places = 3, blank = True)
    mold_nose_coverage = models.PositiveIntegerField(default = 0, blank = True)
    mold_nose_coverage_factor = models.DecimalField(max_digits = 4, decimal_places = 3, blank = True)
    submission = models.ForeignKey('CPLSubmission', on_delete = models.CASCADE, related_name = 'manual_rate')
    
    def get_primary_nose_coverage_factor(self):
        nose = Nose.objects.get(primary_nose_coverage__iexact = self.primary_nose_coverage)
        return nose.factor
    
    def get_mold_nose_coverage_factor(self):
        nose = Nose.objects.get(primary_nose_coverage__iexact = self.mold_nose_coverage)
        return nose.factor
    
    def 
    
class ProfessionalSubmissionManualRate(SubmissionManualRate):
    aggregate_deductible_multiplier = models.PositiveIntegerField(default = 1, blank = True)
    aggregate_deductible_multiplier_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1.000, blank = True)
    state = models.CharField(max_length = 20, default = 'Virginia', blank = True)
    state_factor =  models.DecimalField(max_digits = 4, decimal_places = 3, default = 1.000, blank = True)
    prior_acts_years = models.CharField(max_length = 10, default = 'Full', blank = True)
    prior_acts_years_factor = models.DecimalField(max_digits = 4, decimal_places = 3, default = 1.000, blank = True)
    submission = models.ForeignKey('ProfessionalSubmission', on_delete = models.CASCADE, related_name = 'manual_rate')

class Submission(models.Model):
    submission_total_premium = models.PositiveIntegerField(default = 0, blank = True) 
    
    class Meta:
        abstract = True
        
class CPLSubmission(Submission):
    pass

class ProfessionalSubmission(Submission):
    pass

class SubmissionSet(models.Model):
    cpl_submission = models.OneToOneField('CPLSubmission', on_delete = models.CASCADE, blank = True, null = True, related_name = 'submission_set')
    professional_submission = models.OneToOneField('ProfessionalSubmission', on_delete = models.CASCADE, blank = True, null = True, related_name = 'submission_set')
    bound = models.BooleanField(default = False, blank = True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null = True,
        blank = True
    )
    last_saved = models.DateField(auto_now = True)
    
#come back to this 

class PremiumModifier: #Or, Manual rate cleaner try number 2?
    models_module = importlib.import_module("envirorater.models")
  
    @staticmethod
    def mod_premium(premium, **factor_dict):
        def get_rating_factors(**factor_dict):
            #Check for various types, we can add more later as needed.  Excess k:v
            #pairs will be ignored
            #Also map the types to their respective models
            factor_types = {'deductible' : 'Deductible', 'primary_nose_coverage' : 'Nose', 'mold_nose_coverage' : 'Nose', 
                              'aggregate_deductible_multiplier' : 'Aggregate', 'state' : 'State', 'prior_acts_years' : 'PriorActs' }
            factor_value_dict = {}
            for k in factor_dict:
                if k in factor_types.keys():
                    query = {'{0}__iexact'.format(k) : factor_dict[k]}
                    factor = getattr(PremiumModifier.models_module, factor_types[k]).objects.get(**query).factor
                    factor_value_dict.update({k : factor})
              #Limit factor is a special case that needs two values from the
              #dictionary, so we get it outside of the prior statements since we need
              #both
                if 'limit1' in factor_dict.keys() and 'limit2' in factor_dict.keys():
                    limit_factor = Limit.objects.get(limit1__iexact = factor_dict['limit1'], limit2__iexact = factor_dict['limit2']).factor
                    factor_value_dict.update({'limit' : limit_factor})
            return factor_value_dict    
        factor_value_dict = get_rating_factors(**factor_dict)
        for factor in factor_value_dict.values():
            premium = premium * factor
        return premium
    
    
    


 
  
  
  