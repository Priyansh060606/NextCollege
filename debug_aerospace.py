import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from cutoffs.models import Cutoff
from django.db.models import Q, Max

latest_year = Cutoff.objects.aggregate(Max('year'))['year__max']
print(f"Latest year: {latest_year}")

# Find all Aerospace branches in the database
aero = Cutoff.objects.filter(branch__name__icontains='Aerospace', year=latest_year)
print(f"Total Aerospace cutoffs in {latest_year}: {aero.count()}")

# Get distinct branch names
names = aero.values_list('branch__name', flat=True).distinct()
print(f"Aerospace branch names: {list(names)}")

# Check ALL quotas
quotas = aero.values_list('quota', flat=True).distinct()
print(f"Available quotas for Aerospace: {list(quotas)}")

# Check categories
cats = aero.values_list('category', flat=True).distinct()
print(f"Available categories for Aerospace: {list(cats)}")

# Check seat pools
pools = aero.values_list('seat_pool', flat=True).distinct()
print(f"Available seat pools: {list(pools)}")

# Get ALL unique colleges offering Aerospace (any quota)
all_colleges = aero.values_list('college__name', flat=True).distinct()
print(f"\nALL colleges offering Aerospace ({len(all_colleges)} total):")
for c in sorted(all_colleges):
    print(f"  - {c}")

# Now check with AI/OS filter
aero_ai = aero.filter(quota__in=['AI', 'OS'])
ai_colleges = aero_ai.values_list('college__name', flat=True).distinct()
print(f"\nColleges with Aerospace + AI/OS quota ({len(ai_colleges)}):")
for c in sorted(ai_colleges):
    print(f"  - {c}")

# Check the specific query used for rank 7000
print("\n--- Simulating query for rank 7000, OPEN, Gender-Neutral ---")
student_rank = 7000
lower_bound = max(1, int(student_rank * 0.3))  # 2100
upper_bound = max(int(student_rank * 100), 200000)  # 700000

print(f"Lower bound: {lower_bound}, Upper bound: {upper_bound}")

query = Q(
    year=latest_year,
    category='OPEN',
    seat_pool='Gender-Neutral',
    round_number=1,
    closing_rank__gte=lower_bound,
    closing_rank__lte=upper_bound,
)
query &= Q(quota__in=['AI', 'OS'])

candidates = Cutoff.objects.filter(query).filter(
    branch__name__icontains='Aerospace'
).select_related('college', 'branch').order_by('closing_rank')

print(f"\nResults with round_number=1: {candidates.count()}")
for c in candidates:
    print(f"  R{c.round_number} | {c.college.name[:60]} | {c.branch.name} | CR:{c.closing_rank} | Quota:{c.quota}")

# Now try without round filter
print("\n--- Without round_number filter ---")
query2 = Q(
    year=latest_year,
    category='OPEN',
    seat_pool='Gender-Neutral',
    closing_rank__gte=lower_bound,
    closing_rank__lte=upper_bound,
)
query2 &= Q(quota__in=['AI', 'OS'])

candidates2 = Cutoff.objects.filter(query2).filter(
    branch__name__icontains='Aerospace'
).select_related('college', 'branch').order_by('closing_rank')

print(f"Results without round filter: {candidates2.count()}")
seen = set()
for c in candidates2:
    key = (c.college_id, c.branch_id)
    if key not in seen:
        seen.add(key)
        print(f"  R{c.round_number} | {c.college.name[:60]} | {c.branch.name} | CR:{c.closing_rank} | Quota:{c.quota}")

# Also check: what about Aerospace with very low closing ranks (dream colleges)?
print("\n--- Aerospace entries with closing rank < 2100 (below lower bound) ---")
below = Cutoff.objects.filter(
    branch__name__icontains='Aerospace',
    year=latest_year,
    category='OPEN',
    seat_pool='Gender-Neutral',
    quota__in=['AI', 'OS'],
    closing_rank__lt=lower_bound,
).select_related('college', 'branch').order_by('closing_rank')
for c in below:
    print(f"  R{c.round_number} | {c.college.name[:60]} | {c.branch.name} | CR:{c.closing_rank} | Quota:{c.quota}")

# Check: Aerospace entries with closing rank > upper_bound (should be none due to high cap)
print(f"\n--- Aerospace entries with closing rank > {upper_bound} ---")
above = Cutoff.objects.filter(
    branch__name__icontains='Aerospace',
    year=latest_year,
    category='OPEN',
    seat_pool='Gender-Neutral',
    quota__in=['AI', 'OS'],
    closing_rank__gt=upper_bound,
).count()
print(f"  Count: {above}")

# Check what IIT filter does
print("\n--- Checking IIT filter exclusion ---")
iit_q = (
    Q(college__name__icontains='Indian Institute of Technology') |
    Q(college__name__icontains='Indian Institute  of Technology')
) & ~Q(college__name__icontains='Information Technology') & ~Q(college__name__icontains='Carpet') & ~Q(college__name__icontains='Handloom') & ~Q(college__name__icontains='Engineering Science')

# For Mains: we exclude IITs
non_iit_aero = Cutoff.objects.filter(
    branch__name__icontains='Aerospace',
    year=latest_year,
    category='OPEN',
    seat_pool='Gender-Neutral',
    quota__in=['AI', 'OS'],
).filter(~iit_q).select_related('college', 'branch')

print(f"Non-IIT Aerospace cutoffs: {non_iit_aero.count()}")
non_iit_colleges = non_iit_aero.values_list('college__name', flat=True).distinct()
print(f"Non-IIT colleges offering Aerospace: {list(non_iit_colleges)}")

# IIT Aerospace
iit_aero = Cutoff.objects.filter(
    branch__name__icontains='Aerospace',
    year=latest_year,
    category='OPEN',
    seat_pool='Gender-Neutral',
    quota='AI',
).filter(iit_q).select_related('college', 'branch')

print(f"\nIIT Aerospace cutoffs: {iit_aero.count()}")
iit_aero_colleges = iit_aero.values_list('college__name', flat=True).distinct()
print(f"IIT colleges offering Aerospace: {list(iit_aero_colleges)}")
