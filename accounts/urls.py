from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmpresaViewSet, UsuarioViewSet

router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresas')
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path('', include(router.urls)),
]