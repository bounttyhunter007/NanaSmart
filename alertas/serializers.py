from rest_framework import serializers
from .models import Alerta


class AlertaSerializer(serializers.ModelSerializer):
    ordem_servico_id = serializers.SerializerMethodField()
    ordem_servico_acessivel = serializers.BooleanField(read_only=True, default=False)
    equipamento_nome = serializers.CharField(source='equipamento.nome', read_only=True)
    sensor_nome = serializers.SerializerMethodField()
    legado = serializers.SerializerMethodField()

    class Meta:
        model = Alerta
        fields = [
            'id', 'equipamento', 'sensor', 'tipo_alerta', 'origem',
            'evento_chave', 'dados_analise', 'analise_ia',
            'data_ultima_analise', 'nivel', 'descricao', 'data_alerta',
            'status', 'ordem_servico_id', 'ordem_servico_acessivel', 'equipamento_nome', 'sensor_nome',
            'dados_deteccao', 'data_normalizacao', 'legado', 'historico_niveis',
        ]
        read_only_fields = fields

    def get_ordem_servico_id(self, obj) -> int | None:
        if obj.ordem_servico_id:
            return obj.ordem_servico_id
        try:
            ordem = obj.ordem_servico_preditiva
        except Alerta.ordem_servico_preditiva.RelatedObjectDoesNotExist:
            ordem = None
        return ordem.id if ordem else None

    def get_sensor_nome(self, obj) -> str:
        return obj.sensor.nome if obj.sensor_id else (obj.dados_deteccao or {}).get('sensor_nome', '')

    def get_legado(self, obj) -> bool:
        return not obj.dados_deteccao or obj.dados_deteccao.get('legado', False)
