import os
import random
import pandas as pd
import numpy as np
import joblib
import xgboost as xgb
from django.core.management.base import BaseCommand
from django.conf import settings
from cutoffs.models import Cutoff
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

class Command(BaseCommand):
    help = 'Train XGBoost model for Admission Probability'

    def handle(self, *args, **options):
        self.stdout.write("Fetching historical cutoffs from database...")
        
        # We only need data from the last few rounds or round 6 to define final admission chance.
        # But for simplicity, we'll use all rounds and let XGBoost figure out the patterns.
        # Using a subset of data to avoid memory issues during training.
        cutoffs = Cutoff.objects.filter(closing_rank__gt=0).values(
            'college_id', 'branch_id', 'category', 'seat_pool', 'closing_rank'
        )
        
        if not cutoffs.exists():
            self.stdout.write(self.style.ERROR("No cutoff data found in database. Cannot train model."))
            return
            
        df = pd.DataFrame(list(cutoffs))
        
        self.stdout.write(f"Loaded {len(df)} cutoff records. Generating synthetic training data...")
        
        # Label Encoding
        le_category = LabelEncoder()
        le_seat_pool = LabelEncoder()
        
        df['category_encoded'] = le_category.fit_transform(df['category'])
        df['seat_pool_encoded'] = le_seat_pool.fit_transform(df['seat_pool'])
        
        # Save encoders
        os.makedirs(os.path.join(settings.BASE_DIR, 'ml_models'), exist_ok=True)
        joblib.dump(le_category, os.path.join(settings.BASE_DIR, 'ml_models', 'le_category.pkl'))
        joblib.dump(le_seat_pool, os.path.join(settings.BASE_DIR, 'ml_models', 'le_seat_pool.pkl'))

        # Generate synthetic data
        # For each historical cutoff, generate students who made it (1) and didn't make it (0)
        
        synthetic_data = []
        for row in df.itertuples():
            c_rank = row.closing_rank
            
            # Positive samples (Rank is better/lower than closing rank)
            for _ in range(2):
                student_rank = random.randint(max(1, int(c_rank * 0.5)), c_rank)
                synthetic_data.append([
                    row.college_id, row.branch_id, row.category_encoded, 
                    row.seat_pool_encoded, student_rank, 1
                ])
                
            # Negative samples (Rank is worse/higher than closing rank)
            for _ in range(2):
                student_rank = random.randint(c_rank + 1, int(c_rank * 1.5) + 1000)
                synthetic_data.append([
                    row.college_id, row.branch_id, row.category_encoded, 
                    row.seat_pool_encoded, student_rank, 0
                ])
                
        train_df = pd.DataFrame(synthetic_data, columns=[
            'college_id', 'branch_id', 'category_encoded', 'seat_pool_encoded', 'student_rank', 'admitted'
        ])
        
        self.stdout.write(f"Generated {len(train_df)} training samples. Training XGBoost...")
        
        X = train_df.drop('admitted', axis=1)
        y = train_df['admitted']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = xgb.XGBClassifier(
            objective='binary:logistic',
            n_estimators=100,
            learning_rate=0.1,
            max_depth=6,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        accuracy = model.score(X_test, y_test)
        self.stdout.write(self.style.SUCCESS(f"Model trained successfully! Test Accuracy: {accuracy:.4f}"))
        
        # Save model
        model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'xgboost_admission_model.pkl')
        joblib.dump(model, model_path)
        
        self.stdout.write(self.style.SUCCESS(f"Model saved to {model_path}"))
