from django.urls import path
from .views import AdmissionPredictionView

urlpatterns = [
    path('predict/', AdmissionPredictionView.as_view(), name='predict-admission'),
]
