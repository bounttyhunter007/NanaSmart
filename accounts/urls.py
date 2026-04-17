from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import EmpresaViewSet, UsuarioViewSet, MeView, ChangePasswordView

router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet, basename='empresas')
router.register(r'usuarios', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]