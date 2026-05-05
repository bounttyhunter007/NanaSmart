from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EquipamentoViewSet, EquipamentoLocalizacaoViewSet, PlanoManutencaoViewSet


router = DefaultRouter()

router.register(r'equipamentos', EquipamentoViewSet, basename='equipamentos')
router.register(r'localizacao', EquipamentoLocalizacaoViewSet, basename='localizacao')
router.register(r'planos-manutencao', PlanoManutencaoViewSet, basename='planos-manutencao')

urlpatterns = [
    path('', include(router.urls)),
]