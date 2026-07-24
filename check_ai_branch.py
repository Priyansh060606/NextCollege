import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from cutoffs.models import Cutoff
from colleges.models import College, Branch
from django.db.models import Q, Min, Max

# Find cutoffs for the branch
branch_name = 'Computer Science and Artificial Intelligence (4 Years, Bachelor of Technology)'
cutoffs = Cutoff.objects.filter(branch__name__icontains='Artificial Intelligence').select_related('college', 'branch')
print(f"Total cutoffs with 'Artificial Intelligence': {cutoffs.count()}")

for c in cutoffs[:30]:
    print(f"College: {c.college.name}")
    print(f"  Branch: {c.branch.name}")
    print(f"  Year: {c.year}, Round: {c.round_number}, Category: {c.category}, Seat Pool: {c.seat_pool}")
    print(f"  Opening Rank: {c.opening_rank}, Closing Rank: {c.closing_rank}")
