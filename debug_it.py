import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from cutoffs.models import Cutoff
from django.db.models import Q, Max

ly = Cutoff.objects.aggregate(Max('year'))['year__max']

# Test case 1: rank 1000 without branch filter (old behavior)
print("=== Test 1: Rank 1000, No Branch Filter ===")
rank = 1000
lower = max(1, int(rank * 0.3))
upper = int(rank * 3.5)
print(f"Range: {lower} to {upper}")
q = Q(year=ly, category='OPEN', seat_pool='Gender-Neutral', round_number=1,
      closing_rank__gte=lower, closing_rank__lte=upper, quota__in=['AI', 'OS'])
count = Cutoff.objects.filter(q).count()
print(f"Results: {count}")
print()

# Test case 2: rank 15000 with IT
print("=== Test 2: Rank 15000, Branch=IT ===")
rank = 15000
lower = max(1, int(rank * 0.3))
upper = max(int(rank * 100), 200000)
print(f"Range: {lower} to {upper}")
q = Q(year=ly, category='OPEN', seat_pool='Gender-Neutral', round_number=1,
      closing_rank__gte=lower, closing_rank__lte=upper, quota__in=['AI', 'OS'])
qs = Cutoff.objects.filter(q).filter(branch__name__icontains='Information Technology')
print(f"Results: {qs.count()}")
for c in qs.select_related('college', 'branch')[:5]:
    ratio = c.closing_rank / rank
    if ratio >= 5.0: prob = 98
    elif ratio >= 3.0: prob = int(92 + (ratio - 3.0) / 2.0 * 6)
    elif ratio >= 2.0: prob = int(85 + (ratio - 2.0) / 1.0 * 7)
    elif ratio >= 1.5: prob = int(75 + (ratio - 1.5) / 0.5 * 10)
    elif ratio >= 1.2: prob = int(60 + (ratio - 1.2) / 0.3 * 15)
    elif ratio >= 1.0: prob = int(40 + (ratio - 1.0) / 0.2 * 20)
    elif ratio >= 0.8: prob = int(20 + (ratio - 0.8) / 0.2 * 20)
    elif ratio >= 0.5: prob = int(8 + (ratio - 0.5) / 0.3 * 12)
    else: prob = 5
    status = 'Safe' if prob >= 75 else ('Target' if prob >= 40 else 'Dream')
    print(f"  [{status:6s}] prob={prob}% | CR={c.closing_rank:>6} | ratio={ratio:.2f} | {c.college.name[:40]}")
print()

# Test case 3: rank 50000 with IT
print("=== Test 3: Rank 50000, Branch=IT ===")
rank = 50000
lower = max(1, int(rank * 0.3))
upper = max(int(rank * 100), 200000)
print(f"Range: {lower} to {upper}")
q = Q(year=ly, category='OPEN', seat_pool='Gender-Neutral', round_number=1,
      closing_rank__gte=lower, closing_rank__lte=upper, quota__in=['AI', 'OS'])
qs = Cutoff.objects.filter(q).filter(branch__name__icontains='Information Technology')
print(f"Results: {qs.count()}")
for c in qs.select_related('college', 'branch')[:10]:
    ratio = c.closing_rank / rank
    if ratio >= 5.0: prob = 98
    elif ratio >= 3.0: prob = int(92 + (ratio - 3.0) / 2.0 * 6)
    elif ratio >= 2.0: prob = int(85 + (ratio - 2.0) / 1.0 * 7)
    elif ratio >= 1.5: prob = int(75 + (ratio - 1.5) / 0.5 * 10)
    elif ratio >= 1.2: prob = int(60 + (ratio - 1.2) / 0.3 * 15)
    elif ratio >= 1.0: prob = int(40 + (ratio - 1.0) / 0.2 * 20)
    elif ratio >= 0.8: prob = int(20 + (ratio - 0.8) / 0.2 * 20)
    elif ratio >= 0.5: prob = int(8 + (ratio - 0.5) / 0.3 * 12)
    else: prob = 5
    status = 'Safe' if prob >= 75 else ('Target' if prob >= 40 else 'Dream')
    print(f"  [{status:6s}] prob={prob}% | CR={c.closing_rank:>6} | ratio={ratio:.2f} | {c.college.name[:40]}")
