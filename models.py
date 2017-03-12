from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from decimal import Decimal
# Create your models here.

class ContractorClass(models.Model):
  iso_code = models.PositiveIntegerField(primary_key = True)  
  iso_description = models.CharField(max_length = 140)
  class_relativity = models.DecimalField(max_digits = 3, decimal_places = 2)
  
  def __str__(self):
    return "ISO Code: %s Description: %s" % (self.iso_code, self.iso_description)
  
  def get_premium_ex_mold(self, class_revenue, revenue_band):
    marginal_premium = (class_revenue - revenue_band.start) * revenue_band.factor / 1000
    class_premium_ex_mold = (revenue_band.cumulative_premium + marginal_premium) * self.class_relativity
    return class_premium_ex_mold
  
  def get_mold_premium(self, class_revenue, revenue_band, mold_hazard_group = "low"):
    class_premium_ex_mold = ContractorClass.get_premium_ex_mold(self, class_revenue, revenue_band)
    mold_hazard_group = MoldHazardGroup.objects.get(hazard_group__iexact = mold_hazard_group)
    return class_premium_ex_mold * mold_hazard_group.factor
  
  def get_total_premium(self, class_revenue, revenue_band, mold_hazard_group = "low"):
    return ContractorClass.get_premium_ex_mold(self, class_revenue, revenue_band) + ContractorClass.get_mold_premium(self, class_revenue, revenue_band, mold_hazard_group = "low")
  
class RevenueBand(models.Model):
  start = models.PositiveIntegerField()
  end = models.PositiveIntegerField()
  cumulative_premium = models.PositiveIntegerField()
  factor = models.DecimalField(max_digits = 4, decimal_places = 3)
  
  def __str__(self):
    return "%s - %s Factor: %s" % (self.start, self.end, self.factor)
  
class MoldHazardGroup(models.Model):
  hazard_group = models.CharField(max_length = 20)
  factor = models.DecimalField(max_digits = 4, decimal_places = 3)
  
class Limit(models.Model):
  limit = models.PositiveIntegerField() 
  factor = models.DecimalField(max_digits = 4, decimal_places = 3)
  
class Deductible(models.Model):
  deductible = models.PositiveIntegerField()
  factor = models.DecimalField(max_digits = 4, decimal_places = 3)

class Aggregate(models.Model):
  multiplier = models.PositiveIntegerField()
  factor = models.DecimalField(max_digits = 4, decimal_places = 3)

class Nose(models.Model):
  years = models.PositiveIntegerField()
  factor = models.DecimalField(max_digits = 4, decimal_places = 3)
  
  
  
  