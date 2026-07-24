import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from prediction.ui_views import _RoundWiseResultBase
from django.db.models import Max
from cutoffs.models import Cutoff

# Instantiate the result builder helper
helper = _RoundWiseResultBase()

# Simulate a Mains request for rank 1000
data_mains = helper._build_round_wise_results(
    student_rank=1000,
    category='OPEN',
    gender='Gender-Neutral',
    state='',
    branch_pref='Computer Science and Artificial Intelligence (4 Years, Bachelor of Technology)',
    exam_type='mains'
)

print(f"Mains results count for R1: {len(data_mains['round_data'].get(1, []))}")
if data_mains['round_data'].get(1, []):
    print("Mains R1 results:")
    for r in data_mains['round_data'][1]:
        print(f"  - {r['college_name']}: {r['branch_name']} (Closing: {r['closing_rank']}, Prob: {r['prob']})")

# Simulate an Advanced request for rank 1000
data_adv = helper._build_round_wise_results(
    student_rank=1000,
    category='OPEN',
    gender='Gender-Neutral',
    state='',
    branch_pref='Computer Science and Artificial Intelligence (4 Years, Bachelor of Technology)',
    exam_type='advanced'
)

print(f"Advanced results count for R1: {len(data_adv['round_data'].get(1, []))}")
