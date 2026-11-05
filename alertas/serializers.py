from rest_framework import serializers
from .models import Alerta
from accounts.validation import validate_equipment_resource


class AlertaSerializer(serializers.ModelSerializer):
    ordem_servico_id = serializers.SerializerMethodField()

    class Meta:
        model = Alerta
        fields = [
            'id', 'equipamento', 'sensor', 'tipo_alerta', 'origem',
            'evento_chave', 'dados_analise', 'analise_ia',
            'data_ultima_analise', 'nivel', 'descricao', 'data_alerta',
            'status', 'ordem_servico_id',
        ]
        read_only_fields = [
            'data_alerta', 'data_ultima_analise', 'ordem_servico_id',
            'evento_chave', 'dados_analise', 'analise_ia',
        ]

    def get_ordem_servico_id(self, obj):
        if obj.ordem_servico_id:
            return obj.ordem_servico_id
        try:
            ordem = obj.ordem_servico_preditiva
        except Alerta.ordem_servico_preditiva.RelatedObjectDoesNotExist:
            ordem = None
        return ordem.id if ordem else None

    def validate(self, data):
        if self.instance is None:
            if data.get('origem', 'manual') != 'manual':
                raise serializers.ValidationError({'origem': 'Alertas criados pela API têm origem manual.'})
            data['origem'] = 'manual'
        else:
            if self.instance.ordem_servico_id:
                for campo in ('equipamento', 'sensor'):
                    if campo in data and data[campo] != getattr(self.instance, campo):
                        raise serializers.ValidationError({campo: 'A origem de um alerta vinculado à O.S. não pode ser alterada.'})
            if data.get('origem', self.instance.origem) != self.instance.origem:
                raise serializers.ValidationError({'origem': 'A origem de uma ocorrência não pode ser alterada.'})
            if self.instance.status != 'ativo' and data.get('status') == 'ativo':
                raise serializers.ValidationError({'status': 'Crie outra ocorrência em vez de reabrir o histórico.'})
            if self.instance.origem != 'manual':
                for campo in ('equipamento', 'sensor', 'tipo_alerta', 'nivel', 'descricao'):
                    if campo in data and data[campo] != getattr(self.instance, campo):
                        raise serializers.ValidationError({campo: 'A condição automática é atualizada pelo monitoramento.'})
            if self.instance.origem == 'limite' and 'status' in data:
                permitido = data['status'] == self.instance.status or (
                    self.instance.status == 'ativo' and data['status'] == 'ignorado'
                )
                if not permitido:
                    raise serializers.ValidationError({'status': 'A recuperação por limite é confirmada pelas leituras; é possível ignorar o alerta ativo.'})
        request = self.context.get('request')
        equipamento = data.get('equipamento', getattr(self.instance, 'equipamento', None))
        validate_equipment_resource(
            request.user if request else None,
            equipamento,
        )
        sensor = data.get('sensor', getattr(self.instance, 'sensor', None))
        if sensor and equipamento and sensor.equipamento_id != equipamento.id:
            raise serializers.ValidationError({
                'sensor': 'O sensor deve pertencer ao equipamento informado.'
            })
        return data
