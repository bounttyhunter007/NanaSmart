from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SensorViewSet, TelemetriaViewSet, TrendConfigViewSet, TrendDashboardView

from .demo_views import TrendDemoView, TrendDemoDetailView

router = DefaultRouter()
router.register(r'sensores', SensorViewSet, basename='sensores')
router.register(r'leituras', TelemetriaViewSet, basename='leituras')
router.register(r'trend-config', TrendConfigViewSet, basename='trend-config')

urlpatterns = [
    path('tendencias/demo/', TrendDemoView.as_view(), name='trend-demo'),
    path('tendencias/demo/<uuid:demo_id>/', TrendDemoDetailView.as_view(), name='trend-demo-detail'),
    path('', include(router.urls)),
    path('tendencias/', TrendDashboardView.as_view(), name='trend-dashboard'),
]
