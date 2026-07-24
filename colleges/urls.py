from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CollegeViewSet, BranchViewSet

router = DefaultRouter()
router.register(r'list', CollegeViewSet, basename='college')
router.register(r'branches', BranchViewSet, basename='branch')

urlpatterns = [
    path('', include(router.urls)),
]
