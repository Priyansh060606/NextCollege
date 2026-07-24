from django.db import models

class College(models.Model):
    name = models.CharField(max_length=255, unique=True)
    short_name = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True, null=True)
    is_nirf_ranked = models.BooleanField(default=False)
    nirf_rank = models.IntegerField(blank=True, null=True)
    
    # ROI Fields
    average_fees = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Total course fees in INR")
    average_package = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, help_text="Average placement package in INR (LPA)")

    @property
    def average_fees_lakhs(self):
        if self.average_fees and self.average_fees > 0:
            return round(float(self.average_fees) / 100000.0, 2)
        return None

    def __str__(self):
        return self.name

class Branch(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return self.name
