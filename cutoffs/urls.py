from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CutoffViewSet

router = DefaultRouter()
router.register(r'history', CutoffViewSet, basename='cutoff')

urlpatterns = [
    path('', include(router.urls)),
]
