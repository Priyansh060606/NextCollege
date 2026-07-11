from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Avg, Max
from colleges.models import College, Branch
from cutoffs.models import Cutoff

class DashboardStatsView(APIView):
    """
    Returns high-level statistics and aggregations for the frontend dashboard.
    """
    def get(self, request):
        total_colleges = College.objects.count()
        total_branches = Branch.objects.count()
        total_cutoffs_recorded = Cutoff.objects.count()
        
        # Most competitive branches in the last available year (2025)
        latest_year = Cutoff.objects.aggregate(max_year=Max('year'))['max_year'] or 2025
        
        top_branches = (
            Cutoff.objects.filter(year=latest_year, category='OPEN', round_number=1)
            .values('branch__name')
            .annotate(avg_closing_rank=Avg('closing_rank'))
            .order_by('avg_closing_rank')[:5]
        )
        
        formatted_top_branches = [
            {"branch": b['branch__name'], "avg_closing_rank": int(b['avg_closing_rank'])}
            for b in top_branches if b['avg_closing_rank'] is not None
        ]

        return Response({
            'overview': {
                'total_colleges': total_colleges,
                'total_branches': total_branches,
                'total_historical_records': total_cutoffs_recorded,
            },
            'competitive_insights': {
                'latest_year': latest_year,
                'top_5_most_competitive_branches_open_category': formatted_top_branches
            }
        })
