from rest_framework import serializers
from .models import Alerta
from ativos.models import EquipamentoLocalizacao

class AlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alerta
        fields = '__all__'

class EquipamentoLocalizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipamentoLocalizacao
        fields = '__all__'
