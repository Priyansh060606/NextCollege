import os
import django
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'NextCollege.settings')
django.setup()

from cutoffs.models import Cutoff

# Load models
base_dir = os.path.dirname(os.path.abspath(__file__))
xgb_model_path = os.path.join(base_dir, 'ml_models', 'xgboost_admission_model.pkl')
le_category_path = os.path.join(base_dir, 'ml_models', 'le_category.pkl')
le_seat_pool_path = os.path.join(base_dir, 'ml_models', 'le_seat_pool.pkl')

if not os.path.exists(xgb_model_path):
    print("Model not found")
    exit()

model = joblib.load(xgb_model_path)
le_category = joblib.load(le_category_path)
le_seat_pool = joblib.load(le_seat_pool_path)

# Fetch sample cutoffs
cutoffs = list(Cutoff.objects.all().order_by('?')[:1000])

y_true = []
y_pred_probs = []

features_list = []

for c in cutoffs:
    # True label: if student rank == closing_rank, they got in (1).
    # Let's generate a positive sample (rank = closing_rank * 0.9)
    # and a negative sample (rank = closing_rank * 1.2)
    
    cat = c.category
    try:
        cat_encoded = le_category.transform([cat])[0]
    except ValueError:
        cat_encoded = 0
        
    pool = c.seat_pool
    try:
        pool_encoded = le_seat_pool.transform([pool])[0]
    except ValueError:
        pool_encoded = 0

    # Positive sample
    features_list.append({
        'college_id': c.college_id,
        'branch_id': c.branch_id,
        'category_encoded': cat_encoded,
        'seat_pool_encoded': pool_encoded,
        'student_rank': max(1, int(c.closing_rank * 0.8))
    })
    y_true.append(1)
    
    # Negative sample
    features_list.append({
        'college_id': c.college_id,
        'branch_id': c.branch_id,
        'category_encoded': cat_encoded,
        'seat_pool_encoded': pool_encoded,
        'student_rank': int(c.closing_rank * 1.5)
    })
    y_true.append(0)

df = pd.DataFrame(features_list)
probs = model.predict_proba(df)[:, 1]

y_pred = [1 if p >= 0.5 else 0 for p in probs]
acc = accuracy_score(y_true, y_pred)
print(f"Calculated Accuracy: {acc * 100:.2f}%")
