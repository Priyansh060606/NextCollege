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

    def __str__(self):
        return self.name

class Branch(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, blank=True, null=True)
    
    def __str__(self):
        return self.name

class SeatMatrix(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='seats')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='seats')
    category = models.CharField(max_length=50) # General, OBC, SC, ST, EWS, etc.
    quota = models.CharField(max_length=50)    # HS (Home State), OS (Other State), AI (All India)
    total_seats = models.IntegerField(default=0)

    class Meta:
        unique_together = ('college', 'branch', 'category', 'quota')

    def __str__(self):
        return f"{self.college.short_name or self.college.name} - {self.branch.name} ({self.category})"
