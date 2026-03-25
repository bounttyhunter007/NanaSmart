from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SensorViewSet, TelemetriaViewSet

router = DefaultRouter()
router.register(r'sensores', SensorViewSet)
router.register(r'leituras', TelemetriaViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
