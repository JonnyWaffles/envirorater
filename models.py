from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from decimal import Decimal
# Create your models here.
#I should have made abstract base classes for BaseRateClass (ContractorClass and ProfessionalClass)
#and RevenueBand, but I don't want to have to rebuild those tables during testing...

class ContractorClass(models.Model):
    iso_code = models.PositiveIntegerField(primary_key = True)  
    iso_description = models.CharField(max_length = 140)
    class_relativity = models.DecimalField(max_digits = 3, decimal_places = 2)
  
    def __str__(self):
        return "ISO Code: %s Description: %s" % (self.iso_code, self.iso_description)
  #Can refactor this later since the only difference between this and the professional liability is
  #The mold premium
    def get_premium_ex_mold(self, revenue = 0):
        revenue_band = ContractorsPollutionRevenueBand.objects.get(start__lt = revenue, end__gte = revenue)
        marginal_premium = (revenue - revenue_band.start) * revenue_band.factor / 1000
        class_premium_ex_mold = (revenue_band.cumulative_premium + marginal_premium) * self.class_relativity
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
    class_relativity = models.DecimalField(max_digits = 3, decimal_places = 2)
  
    def __str__(self):
        return "ISO Code: %s Description: %s" % (self.iso_code, self.iso_description)
  
    def get_premium(self, revenue = 0):
        revenue_band = ProfessionalRevenueBand.objects.get(start__lt = revenue, end__gte = revenue)
        marginal_premium = (revenue - revenue_band.start) * revenue_band.factor / 1000
        premium = (revenue_band.cumulative_premium + marginal_premium) * self.class_relativity
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

class SubmissionBaseRate(models.Model):
    iso_code = models.PositiveIntegerField()  
    iso_description = models.CharField(max_length = 140)
    class_relativity = models.DecimalField(max_digits = 3, decimal_places = 2)
  
  
  