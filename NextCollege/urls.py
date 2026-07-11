"""
URL configuration for NextCollege project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from prediction.ui_views import (
    HomeView, PredictorView, ResultView, RecommendationView,
    CollegeListView, CollegeDetailView, AnalyticsView, ReportView,
    LoginView, RegisterView, ROIAnalysisView, ChatView
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('predict/', PredictorView.as_view(), name='predict'),
    path('result/', ResultView.as_view(), name='result'),
    path('recommend/', RecommendationView.as_view(), name='recommend'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('roi-analysis/', ROIAnalysisView.as_view(), name='roi_analysis'),
    path('colleges/', CollegeListView.as_view(), name='college_list'),
    path('colleges/<int:college_id>/', CollegeDetailView.as_view(), name='college_detail'),
    path('report/', ReportView.as_view(), name='report'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('admin/', admin.site.urls),
    path('api/colleges/', include('colleges.urls')),
    path('api/cutoffs/', include('cutoffs.urls')),
    path('api/prediction/', include('prediction.urls')),
    path('api/recommendations/', include('recommendation.urls')),
    path('api/analytics/', include('analytics.urls')),
]
