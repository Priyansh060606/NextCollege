import os
import joblib
import pandas as pd
from prophet import Prophet
from django.conf import settings
from cutoffs.models import Cutoff

class PredictionService:
    def __init__(self):
        self.xgb_model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'xgboost_admission_model.pkl')
        self.le_category_path = os.path.join(settings.BASE_DIR, 'ml_models', 'le_category.pkl')
        self.le_seat_pool_path = os.path.join(settings.BASE_DIR, 'ml_models', 'le_seat_pool.pkl')
        
        self.model = None
        self.le_category = None
        self.le_seat_pool = None

    def _load_models(self):
        if not self.model and os.path.exists(self.xgb_model_path):
            self.model = joblib.load(self.xgb_model_path)
            self.le_category = joblib.load(self.le_category_path)
            self.le_seat_pool = joblib.load(self.le_seat_pool_path)

    def predict_admission_probability(self, college_id, branch_id, category, seat_pool, student_rank):
        """Returns the admission probability using the XGBoost model."""
        self._load_models()
        if not self.model:
            return None # Model not trained yet
            
        try:
            cat_encoded = self.le_category.transform([category])[0]
        except ValueError:
            cat_encoded = 0 # Default to 0 if unknown
            
        try:
            pool_encoded = self.le_seat_pool.transform([seat_pool])[0]
        except ValueError:
            pool_encoded = 0

        # Features: 'college_id', 'branch_id', 'category_encoded', 'seat_pool_encoded', 'student_rank'
        features = pd.DataFrame([{
            'college_id': college_id,
            'branch_id': branch_id,
            'category_encoded': cat_encoded,
            'seat_pool_encoded': pool_encoded,
            'student_rank': student_rank
        }])
        
        # predict_proba returns [[prob_0, prob_1]]
        probability = self.model.predict_proba(features)[0][1]
        return int(round(probability * 100, 0))

    def predict_batch(self, inputs):
        """
        Returns probabilities for a batch of inputs to drastically speed up recommendation engine.
        inputs is a list of dicts: [{'college_id': 1, 'branch_id': 2, 'category': 'OPEN', 'seat_pool': '...', 'student_rank': 500}]
        """
        self._load_models()
        if not self.model or not inputs:
            return []

        df = pd.DataFrame(inputs)
        
        # Batch transform categories
        known_cats = set(self.le_category.classes_)
        df['category_encoded'] = df['category'].apply(
            lambda x: self.le_category.transform([x])[0] if x in known_cats else 0
        )
        
        known_pools = set(self.le_seat_pool.classes_)
        df['seat_pool_encoded'] = df['seat_pool'].apply(
            lambda x: self.le_seat_pool.transform([x])[0] if x in known_pools else 0
        )
        
        features = df[['college_id', 'branch_id', 'category_encoded', 'seat_pool_encoded', 'student_rank']]
        
        # Predict all at once
        probs = self.model.predict_proba(features)[:, 1]
        
        return [int(round(p * 100, 0)) for p in probs]


    def forecast_cutoff(self, college_id, branch_id, category, seat_pool):
        """Uses Prophet to forecast the cutoff for the upcoming year (2026)."""
        history = Cutoff.objects.filter(
            college_id=college_id, 
            branch_id=branch_id, 
            category=category, 
            seat_pool=seat_pool,
            round_number=1  # Standardize on round 1 or 6
        ).order_by('year').values('year', 'closing_rank')
        
        if len(history) < 3:
            return None # Not enough data to forecast reliably
            
        # Prepare data for Prophet
        df = pd.DataFrame(list(history))
        # Prophet requires 'ds' (datetime) and 'y' (target)
        df['ds'] = pd.to_datetime(df['year'], format='%Y')
        df['y'] = df['closing_rank']
        
        m = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False)
        m.fit(df)
        
        # Predict for the next 1 year (2026)
        future = m.make_future_dataframe(periods=1, freq='Y')
        forecast = m.predict(future)
        
        # Get the prediction for the last row
        predicted_rank = int(forecast.iloc[-1]['yhat'])
        return max(1, predicted_rank) # Rank can't be negative
