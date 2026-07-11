from django.db import models
from colleges.models import College, Branch

class Cutoff(models.Model):
    college = models.ForeignKey(College, on_delete=models.CASCADE, related_name='cutoffs')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='cutoffs')
    
    year = models.IntegerField(help_text="Year of counseling (e.g., 2023)")
    round_number = models.IntegerField(help_text="Counseling round number")
    
    category = models.CharField(max_length=50, help_text="e.g., OPEN, OBC-NCL, SC, ST")
    quota = models.CharField(max_length=50, help_text="e.g., AI (All India), HS (Home State)")
    seat_pool = models.CharField(max_length=50, default='Gender-Neutral', help_text="e.g., Gender-Neutral, Female-Only")
    
    opening_rank = models.IntegerField()
    closing_rank = models.IntegerField()

    class Meta:
        unique_together = ('college', 'branch', 'year', 'round_number', 'category', 'quota', 'seat_pool')
        ordering = ['-year', 'round_number', 'college', 'branch']

    def __str__(self):
        return f"{self.college.short_name or self.college.name} | {self.branch.name} | {self.year} R{self.round_number} | {self.category} | CR: {self.closing_rank}"
