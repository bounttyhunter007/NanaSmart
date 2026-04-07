from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrdemServicoViewSet, HistoricoManutencaoViewSet

router = DefaultRouter()
# A rota vai se chamar 'ordens-servico'
router.register(r'ordens-servico', OrdemServicoViewSet, basename='ordens-servico')
router.register(r'historico', HistoricoManutencaoViewSet, basename='historico')

urlpatterns = [
    path('', include(router.urls)),
]