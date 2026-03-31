from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import EmpresaViewSet, UsuarioViewSet, MeView

router = DefaultRouter()
router.register(r'empresas', EmpresaViewSet)
router.register(r'usuarios', UsuarioViewSet)

urlpatterns = [
    path('', include(router.urls)),

    # --- Autenticação JWT ---
    path('auth/login/',   TokenObtainPairView.as_view(),  name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(),     name='token_refresh'),
    path('auth/me/',      MeView.as_view(),               name='auth_me'),
]