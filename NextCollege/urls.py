"""
URL configuration for NextCollege project.
"""
from django.urls import path, include
from django.views.generic import TemplateView
from prediction.ui_views import (
    HomeView, PredictorView, ResultView, RecommendationView,
    CollegeListView, CollegeDetailView, AnalyticsView, ReportView,
    ROIAnalysisView, ChatView,
    MainsPredictorView, AdvancedPredictorView, MainsResultView, AdvancedResultView,
    ModelInspectorView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('predict/', PredictorView.as_view(), name='predict'),
    path('predict/mains/', MainsPredictorView.as_view(), name='predict_mains'),
    path('predict/advanced/', AdvancedPredictorView.as_view(), name='predict_advanced'),
    path('result/', ResultView.as_view(), name='result'),
    path('result/mains/', MainsResultView.as_view(), name='result_mains'),
    path('result/advanced/', AdvancedResultView.as_view(), name='result_advanced'),
    path('recommend/', RecommendationView.as_view(), name='recommend'),
    path('analytics/', AnalyticsView.as_view(), name='analytics'),
    path('roi-analysis/', ROIAnalysisView.as_view(), name='roi_analysis'),
    path('colleges/', CollegeListView.as_view(), name='college_list'),
    path('colleges/<int:college_id>/', CollegeDetailView.as_view(), name='college_detail'),
    path('report/', ReportView.as_view(), name='report'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('models/', ModelInspectorView.as_view(), name='model_inspector'),

    path('api/colleges/', include('colleges.urls')),
    path('api/cutoffs/', include('cutoffs.urls')),
    path('api/prediction/', include('prediction.urls')),
    path('api/recommendations/', include('recommendation.urls')),
    path('api/analytics/', include('analytics.urls')),
]

