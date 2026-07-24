import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from cutoffs.models import Cutoff
from django.db.models import Min, Max

cutoffs = Cutoff.objects.filter(branch__name='Computer Science and Artificial Intelligence (4 Years, Bachelor of Technology)').select_related('college')
print(f"Total cutoffs: {cutoffs.count()}")
for c in cutoffs[:10]:
    print(f"College: {c.college.name}, Year: {c.year}, Round: {c.round_number}, Category: {c.category}, Pool: {c.seat_pool}, Quota: {c.quota}, Closing: {c.closing_rank}")
