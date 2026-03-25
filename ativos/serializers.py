from rest_framework import serializers
from .models import Equipamento, EquipamentoLocalizacao

class EquipamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipamento
        fields = '__all__' # Transforma todos os campos do Model em JSON

class EquipamentoLocalizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipamentoLocalizacao
        fields = '__all__'