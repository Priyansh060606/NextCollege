import os
import joblib
import pandas as pd
try:
    from prophet import Prophet
except ImportError:
    Prophet = None
from django.conf import settings
from cutoffs.models import Cutoff

class PredictionService:
    def __init__(self):
        self.xgb_model_path = os.path.join(settings.BASE_DIR, 'ml_models', 'xgboost_admission_model.pkl')
        
        self.le_college_path = os.path.join(settings.BASE_DIR, 'ml_models', 'le_college.pkl')
        self.le_branch_path = os.path.join(settings.BASE_DIR, 'ml_models', 'le_branch.pkl')
        self.le_category_path = os.path.join(settings.BASE_DIR, 'ml_models', 'le_category.pkl')
        self.le_seat_pool_path = os.path.join(settings.BASE_DIR, 'ml_models', 'le_seat_pool.pkl')
        
        self.models = {}
        self.le_college = None
        self.le_branch = None
        self.le_category = None
        self.le_seat_pool = None

    def _load_models(self):
        if not self.le_category and os.path.exists(self.le_category_path):
            self.le_college = joblib.load(self.le_college_path)
            self.le_branch = joblib.load(self.le_branch_path)
            self.le_category = joblib.load(self.le_category_path)
            self.le_seat_pool = joblib.load(self.le_seat_pool_path)
            
        if 'xgboost' not in self.models and os.path.exists(self.xgb_model_path):
            self.models['xgboost'] = joblib.load(self.xgb_model_path)

    def predict_admission_probability(self, college_id, branch_id, category, seat_pool, student_rank, model_type='xgboost'):
        """Returns the admission probability using the specified model."""
        self._load_models()
        
        model = self.models.get(model_type)
        if not model:
            return None # Model not trained yet
            
        # Get college and branch names
        from colleges.models import College, Branch
        try:
            college = College.objects.get(id=college_id)
            branch = Branch.objects.get(id=branch_id)
        except (College.DoesNotExist, Branch.DoesNotExist):
            return 0
            
        try:
            col_encoded = self.le_college.transform([college.name])[0]
        except ValueError:
            col_encoded = 0
            
        try:
            br_encoded = self.le_branch.transform([branch.name])[0]
        except ValueError:
            br_encoded = 0
            
        try:
            cat_encoded = self.le_category.transform([category])[0]
        except ValueError:
            cat_encoded = 0 # Default to 0 if unknown
            
        try:
            pool_encoded = self.le_seat_pool.transform([seat_pool])[0]
        except ValueError:
            pool_encoded = 0

        features = pd.DataFrame([{
            'college_encoded': col_encoded,
            'branch_encoded': br_encoded,
            'category_encoded': cat_encoded,
            'seat_pool_encoded': pool_encoded,
            'student_rank': student_rank
        }])
        
        probability = model.predict_proba(features)[0][1]
        return int(round(probability * 100, 0))

    def predict_batch(self, inputs, model_type='xgboost'):
        """
        Returns probabilities for a batch of inputs to drastically speed up recommendation engine.
        """
        self._load_models()
        model = self.models.get(model_type)
        if not model or not inputs:
            return []

        df = pd.DataFrame(inputs)
        
        from colleges.models import College, Branch
        
        def safe_encode(encoder, val):
            try:
                return encoder.transform([val])[0]
            except ValueError:
                return 0
                
        # Resolve names and encode
        college_cache = {c.id: c.name for c in College.objects.all()}
        branch_cache = {b.id: b.name for b in Branch.objects.all()}
        
        df['college_encoded'] = df['college_id'].map(college_cache).apply(lambda x: safe_encode(self.le_college, x))
        df['branch_encoded'] = df['branch_id'].map(branch_cache).apply(lambda x: safe_encode(self.le_branch, x))
        
        df['category_encoded'] = df['category'].apply(lambda x: safe_encode(self.le_category, x))
        df['seat_pool_encoded'] = df['seat_pool'].apply(lambda x: safe_encode(self.le_seat_pool, x))
        
        features = df[['college_encoded', 'branch_encoded', 'category_encoded', 'seat_pool_encoded', 'student_rank']]
        
        probs = model.predict_proba(features)[:, 1]
        
        return [int(round(p * 100, 0)) for p in probs]


    def forecast_cutoff(self, college_id, branch_id, category, seat_pool, model_type='prophet'):
        """Forecasts the cutoff for the upcoming year (2026)."""

            
        # Default Prophet behavior
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
        
        if not Prophet: return None
        m = Prophet(yearly_seasonality=False, weekly_seasonality=False, daily_seasonality=False)
        m.fit(df)
        
        # Predict for the next 1 year (2026)
        future = m.make_future_dataframe(periods=1, freq='Y')
        forecast = m.predict(future)
        
        # Get the prediction for the last row
        predicted_rank = int(forecast.iloc[-1]['yhat'])
        return max(1, predicted_rank) # Rank can't be negative
