from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import College, Branch, SeatMatrix
from .serializers import CollegeSerializer, BranchSerializer, SeatMatrixSerializer

class CollegeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = College.objects.all().order_by('name')
    serializer_class = CollegeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['state', 'is_nirf_ranked']
    search_fields = ['name', 'short_name']

class BranchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Branch.objects.all().order_by('name')
    serializer_class = BranchSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

class SeatMatrixViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SeatMatrix.objects.all().select_related('college', 'branch')
    serializer_class = SeatMatrixSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['college', 'branch', 'category', 'quota']
