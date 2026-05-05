from rest_framework import serializers
from .models import Equipamento, EquipamentoLocalizacao, PlanoManutencao

class EquipamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipamento
        fields = '__all__' 

class EquipamentoLocalizacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipamentoLocalizacao
        fields = '__all__'

class PlanoManutencaoSerializer(serializers.ModelSerializer):
    proximo_disparo_horas = serializers.SerializerMethodField()

    class Meta:
        model = PlanoManutencao
        fields = '__all__'
        read_only_fields = ['horimetro_ultima_os']

    def get_proximo_disparo_horas(self, obj):
        """Calcula e exibe quando a próxima O.S. será gerada."""
        return obj.horimetro_ultima_os + obj.intervalo_horas