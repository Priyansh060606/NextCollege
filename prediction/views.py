from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import PredictionService

class AdmissionPredictionView(APIView):
    """
    Predicts the admission probability and forecasts the future cutoff.
    """
    def post(self, request):
        college_id = request.data.get('college_id')
        branch_id = request.data.get('branch_id')
        category = request.data.get('category')
        seat_pool = request.data.get('seat_pool', 'Gender-Neutral')
        student_rank = request.data.get('student_rank')
        
        if not all([college_id, branch_id, category, student_rank]):
            return Response({'error': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            student_rank = int(student_rank)
        except ValueError:
            return Response({'error': 'student_rank must be an integer'}, status=status.HTTP_400_BAD_REQUEST)

        service = PredictionService()
        
        # ML Model 1: Probability
        probability = service.predict_admission_probability(
            college_id, branch_id, category, seat_pool, student_rank
        )
        
        # ML Model 2: Forecasting using Prophet
        forecast_rank = service.forecast_cutoff(
            college_id, branch_id, category, seat_pool
        )
        
        if probability is None:
            return Response({
                'error': 'ML Model is not trained yet. Run `python manage.py train_xgboost`.'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({
            'college_id': college_id,
            'branch_id': branch_id,
            'category': category,
            'student_rank': student_rank,
            'admission_probability': f"{probability}%",
            'forecasted_2026_cutoff': forecast_rank
        }, status=status.HTTP_200_OK)
