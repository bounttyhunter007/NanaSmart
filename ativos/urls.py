from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (EquipamentoViewSet, EquipamentoLocalizacaoViewSet, PlanoManutencaoViewSet,
                    TipoEquipamentoViewSet, HistoricoCriticidadeEquipamentoViewSet, CriteriosCriticidadeViewSet)


router = DefaultRouter()

router.register(r'equipamentos', EquipamentoViewSet, basename='equipamentos')
router.register(r'localizacao', EquipamentoLocalizacaoViewSet, basename='localizacao')
router.register(r'planos-manutencao', PlanoManutencaoViewSet, basename='planos-manutencao')
router.register(r'tipos-equipamento', TipoEquipamentoViewSet, basename='tipos-equipamento')
router.register(r'historico-criticidade', HistoricoCriticidadeEquipamentoViewSet, basename='historico-criticidade')
router.register(r'criterios-criticidade', CriteriosCriticidadeViewSet, basename='criterios-criticidade')

urlpatterns = [
    path('', include(router.urls)),
]
