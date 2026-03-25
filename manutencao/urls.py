from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrdemServicoViewSet, HistoricoManutencaoViewSet

router = DefaultRouter()
# A rota vai se chamar 'ordens-servico'
router.register(r'ordens-servico', OrdemServicoViewSet)
router.register(r'historico', HistoricoManutencaoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]