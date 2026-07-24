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

branches = list(
    Cutoff.objects.filter(iit_cutoff_q)
    .values_list('branch__name', flat=True)
    .distinct()
    .order_by('branch__name')
)

print(f"Total branches: {len(branches)}")
target = 'Computer Science and Artificial Intelligence (4 Years, Bachelor of Technology)'
print(f"Is target in IIT branches? {target in branches}")
