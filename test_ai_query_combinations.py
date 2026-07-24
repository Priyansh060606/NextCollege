import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from prediction.ui_views import _RoundWiseResultBase
from colleges.models import College, Branch
from cutoffs.models import Cutoff

helper = _RoundWiseResultBase()

categories = ['OPEN', 'OBC-NCL', 'SC', 'ST', 'EWS']
genders = ['Gender-Neutral', 'Female-only (including Supernumerary)']

for cat in categories:
    for gen in genders:
        data = helper._build_round_wise_results(
            student_rank=1000,
            category=cat,
            gender=gen,
            state='',
            branch_pref='Computer Science and Artificial Intelligence (4 Years, Bachelor of Technology)',
            exam_type='mains'
        )
        print(f"Cat: {cat}, Gen: {gen} -> Round 1 Results: {len(data['round_data'].get(1, []))}")
        if len(data['round_data'].get(1, [])) > 0:
            for r in data['round_data'][1]:
                print(f"   - {r['college_name']} ({r['status']}, Closing: {r['closing_rank']})")
