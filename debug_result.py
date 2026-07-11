import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from cutoffs.models import Cutoff
from colleges.models import College
from django.db.models import Q, Max

rank = 567
ly = 2025
category = 'OPEN'
gender = 'Gender-Neutral'
state = 'Maharashtra'

print(f"=== Debugging ResultView for rank={rank}, state={state} ===\n")

# Step 1: What does the query look like?
query = Q(
    year=ly,
    category=category,
    seat_pool=gender,
    round_number=1,
    closing_rank__gte=max(1, int(rank * 0.5)),  # 283
    closing_rank__lte=int(rank * 2.5),  # 1417
)
print(f"Closing rank range: {max(1, int(rank*0.5))} to {int(rank*2.5)}")

# Without state filter
base_qs = Cutoff.objects.filter(query)
print(f"\nBase query (no quota filter): {base_qs.count()} results")

# With state filter 
query_with_state = query & (Q(quota__in=['AI', 'OS']) | Q(quota='HS', college__state__iexact=state))
qs = Cutoff.objects.filter(query_with_state).select_related('college', 'branch').order_by('closing_rank')
print(f"With state filter (AI/OS/HS-Maharashtra): {qs.count()} results")

# Check if Maharashtra colleges exist
mh_colleges = College.objects.filter(state__iexact='Maharashtra')
print(f"\nColleges in Maharashtra: {mh_colleges.count()}")
for c in mh_colleges[:5]:
    print(f"  - {c.name} (state='{c.state}')")

# Check some actual results
print(f"\n--- First 10 matching cutoffs ---")
for c in qs[:10]:
    ratio = c.closing_rank / max(rank, 1)
    if ratio > 1.5:
        prob = min(98, 70 + ratio * 10)
    elif ratio > 1.0:
        prob = 40 + (ratio - 1.0) * 60
    elif ratio > 0.7:
        prob = 10 + (ratio - 0.7) * 100
    else:
        prob = max(5, ratio * 15)
    prob = int(round(prob, 0))
    
    if prob >= 75:
        status = 'Safe'
    elif prob >= 40:
        status = 'Target'
    else:
        status = 'Dream'
    
    print(f"  {c.college.name[:50]:50s} | {c.branch.name[:30]:30s} | CR={c.closing_rank:>6} | Q={c.quota:>2} | ratio={ratio:.2f} | prob={prob}% | {status}")

# Check what template sees
print(f"\n--- Checking template logic ---")
print(f"Template data-category thresholds: dream < 40, target 40-74, safe >= 75")
print(f"Tab filters: dream, target, safe")

# Simulate full result building
seen = set()
unique_candidates = []
for c in qs:
    key = (c.college_id, c.branch_id)
    if key not in seen:
        seen.add(key)
        unique_candidates.append(c)

results = []
for cand in unique_candidates:
    ratio = cand.closing_rank / max(rank, 1)
    if ratio > 1.5:
        prob = min(98, 70 + ratio * 10)
    elif ratio > 1.0:
        prob = 40 + (ratio - 1.0) * 60
    elif ratio > 0.7:
        prob = 10 + (ratio - 0.7) * 100
    else:
        prob = max(5, ratio * 15)
    prob = int(round(prob, 0))
    
    if prob >= 75:
        status = 'Safe'
    elif prob >= 40:
        status = 'Target'
    else:
        status = 'Dream'
    
    results.append({'status': status, 'prob': prob, 'college': cand.college.name, 'branch': cand.branch.name})

safe = [r for r in results if r['status'] == 'Safe']
target = [r for r in results if r['status'] == 'Target']
dream = [r for r in results if r['status'] == 'Dream']

print(f"\nTotal unique results: {len(results)}")
print(f"  Safe: {len(safe)}")
print(f"  Target: {len(target)}")
print(f"  Dream: {len(dream)}")

# But the template's data-category uses different thresholds!
# Template: prob < 40 -> dream, prob < 75 -> target, else safe
# View: prob >= 75 -> Safe, prob >= 40 -> Target, else Dream
# These match! So what's wrong?

print(f"\nBalanced results sent to template:")
safe_results = safe[:20]
target_results = target[:20]
dream_results = dream[:20]
balanced = safe_results + target_results + dream_results
print(f"  Total balanced: {len(balanced)}")
