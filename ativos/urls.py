from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EquipamentoViewSet, EquipamentoLocalizacaoViewSet

# 1. Instancia o roteador
router = DefaultRouter()

# 2. Registra o ViewSet no roteador
# ativos/urls.py
router.register(r'equipamentos', EquipamentoViewSet, basename='equipamentos')
router.register(r'localizacao', EquipamentoLocalizacaoViewSet, basename='localizacao')

# 3. Disponibiliza a rota
urlpatterns = [
    path('', include(router.urls)),
]