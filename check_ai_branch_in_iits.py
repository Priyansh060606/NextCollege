import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from cutoffs.models import Cutoff
from django.db.models import Q

iit_cutoff_q = (
    Q(college__name__icontains='Indian Institute of Technology') |
    Q(college__name__icontains='Indian Institute  of Technology')
) & ~Q(college__name__icontains='Information Technology') & ~Q(college__name__icontains='Carpet') & ~Q(college__name__icontains='Handloom') & ~Q(college__name__icontains='Engineering Science')

# Check if there are any cutoffs for this branch in IITs
iit_count = Cutoff.objects.filter(iit_cutoff_q, branch__name='Computer Science and Artificial Intelligence (4 Years, Bachelor of Technology)').count()
print(f"IIT cutoffs for this branch: {iit_count}")

# Check if there are any cutoffs for this branch in non-IITs
non_iit_count = Cutoff.objects.filter(~iit_cutoff_q, branch__name='Computer Science and Artificial Intelligence (4 Years, Bachelor of Technology)').count()
print(f"Non-IIT cutoffs for this branch: {non_iit_count}")
