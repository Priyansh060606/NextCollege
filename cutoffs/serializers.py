from rest_framework import serializers
from .models import Cutoff

class CutoffSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source='college.name', read_only=True)
    branch_name = serializers.CharField(source='branch.name', read_only=True)

    class Meta:
        model = Cutoff
        fields = [
            'id', 'college', 'college_name', 'branch', 'branch_name',
            'year', 'round_number', 'category', 'quota', 'seat_pool',
            'opening_rank', 'closing_rank'
        ]
