from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .engine import RecommendationEngine

class CounselorStrategyView(APIView):
    """
    Acts as the AI Counselor, generating a personalized list of Dream, Target, and Safe colleges.
    """
    def post(self, request):
        student_rank = request.data.get('student_rank')
        category = request.data.get('category')
        seat_pool = request.data.get('seat_pool', 'Gender-Neutral')
        state = request.data.get('state', None)

        if not all([student_rank, category]):
            return Response(
                {'error': 'Missing required fields: student_rank, category'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student_rank = int(student_rank)
        except ValueError:
            return Response(
                {'error': 'student_rank must be an integer'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        engine = RecommendationEngine()
        strategy = engine.generate_strategy(
            student_rank=student_rank,
            category=category,
            seat_pool=seat_pool,
            state=state
        )

        return Response({
            'student_profile': {
                'rank': student_rank,
                'category': category,
                'seat_pool': seat_pool,
                'state': state
            },
            'strategy': strategy
        }, status=status.HTTP_200_OK)
