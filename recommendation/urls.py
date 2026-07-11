from django.urls import path
from .views import CounselorStrategyView

urlpatterns = [
    path('strategy/', CounselorStrategyView.as_view(), name='counselor-strategy'),
]
