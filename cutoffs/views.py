from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from .models import Cutoff
from .serializers import CutoffSerializer
import django_filters

class CutoffFilter(django_filters.FilterSet):
    min_year = django_filters.NumberFilter(field_name="year", lookup_expr='gte')
    max_year = django_filters.NumberFilter(field_name="year", lookup_expr='lte')
    max_closing_rank = django_filters.NumberFilter(field_name="closing_rank", lookup_expr='lte')

    class Meta:
        model = Cutoff
        fields = ['college', 'branch', 'year', 'round_number', 'category', 'quota', 'seat_pool']

class CutoffViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cutoff.objects.all().select_related('college', 'branch')
    serializer_class = CutoffSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = CutoffFilter
    ordering_fields = ['year', 'round_number', 'closing_rank']
