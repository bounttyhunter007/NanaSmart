from rest_framework import serializers
from .models import OrdemServico, HistoricoManutencao
from accounts.validation import validate_company_resource
from .services import PrioridadeOSService

class OrdemServicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdemServico
        fields = '__all__'
        
        # A magia da segurança Sênior acontece aqui:
        read_only_fields = [
            'data_abertura', 'data_conclusao', 'prioridade_automatica',
            'justificativa_prioridade', 'criticidade_na_abertura',
            'justificativa_criticidade_na_abertura', 'prioridade_manual',
            'alerta_origem', 'sensor_origem',
        ]

    def validate(self, data):
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        equipamento = data.get('equipamento', getattr(self.instance, 'equipamento', None))
        responsavel = data.get('responsavel', getattr(self.instance, 'responsavel', None))

        if user and user.tipo_usuario != 'admin' and equipamento and equipamento.empresa_id != user.empresa_id:
            raise serializers.ValidationError({'equipamento': 'O equipamento deve pertencer à sua empresa.'})

        if responsavel and equipamento and responsavel.empresa_id != equipamento.empresa_id:
            if responsavel.tipo_usuario != 'admin':
                raise serializers.ValidationError({'responsavel': 'O responsável deve pertencer à empresa do equipamento.'})

        if user and user.tipo_usuario == 'tecnico':
            if responsavel and responsavel != user:
                raise serializers.ValidationError({
                    'responsavel': 'Técnicos só podem assumir ordens para si mesmos.'
                })

            if self.instance and self.instance.responsavel and self.instance.responsavel != user:
                raise serializers.ValidationError('Técnicos não podem editar ordens atribuídas a outro técnico.')

        if self.instance and self.instance.status in ('concluida', 'cancelada'):
            if data.get('status', self.instance.status) != self.instance.status:
                raise serializers.ValidationError({'status': 'Uma ordem concluída ou cancelada não pode mudar de status.'})

        sensor = getattr(self.instance, 'sensor_origem', None)
        alerta = getattr(self.instance, 'alerta_origem', None)
        if equipamento and ((sensor and sensor.equipamento_id != equipamento.pk)
                            or (alerta and alerta.equipamento_id != equipamento.pk)):
            raise serializers.ValidationError({'equipamento': 'O equipamento deve corresponder à origem da ordem.'})

        return data

    def create(self, validated_data):
        request = self.context.get('request')
        prioridade_informada = 'prioridade' in self.initial_data
        if prioridade_informada and request and request.user.tipo_usuario in ['gestor', 'admin']:
            validated_data['prioridade_manual'] = True
            validated_data['prioridade_automatica'] = validated_data['prioridade']
            validated_data['justificativa_prioridade'] = 'Prioridade definida manualmente por usuário autorizado.'
        else:
            validated_data.pop('prioridade', None)
            PrioridadeOSService.preencher(validated_data, validated_data['equipamento'])
        if request and request.user.is_authenticated and request.user.tipo_usuario == 'tecnico':
            responsavel = validated_data.get('responsavel')
            if responsavel is None and validated_data.get('status') in ['andamento', 'concluida']:
                validated_data['responsavel'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        prioridade_informada = 'prioridade' in self.initial_data
        if prioridade_informada and request and request.user.tipo_usuario in ['gestor', 'admin']:
            validated_data['prioridade_manual'] = True
            validated_data['prioridade_automatica'] = validated_data['prioridade']
            validated_data['justificativa_prioridade'] = 'Prioridade definida manualmente por usuário autorizado.'
        elif not instance.prioridade_manual:
            validated_data.pop('prioridade', None)
            dados_calculo = {
                'tipo_os': validated_data.get('tipo_os', instance.tipo_os),
                'gravidade_condicao': validated_data.get('gravidade_condicao', instance.gravidade_condicao),
                'risco_seguranca': validated_data.get('risco_seguranca', instance.risco_seguranca),
            }
            PrioridadeOSService.preencher(dados_calculo, validated_data.get('equipamento', instance.equipamento))
            dados_calculo.pop('criticidade_na_abertura', None)
            dados_calculo.pop('justificativa_criticidade_na_abertura', None)
            validated_data.update(dados_calculo)
        else:
            validated_data.pop('prioridade', None)
        if request and request.user.is_authenticated and request.user.tipo_usuario == 'tecnico':
            responsavel = validated_data.get('responsavel', instance.responsavel)
            if instance.responsavel is None and responsavel is None:
                validated_data['responsavel'] = request.user
            if validated_data.get('status') == 'concluida' and validated_data.get('responsavel') is None:
                validated_data['responsavel'] = request.user
        return super().update(instance, validated_data)

class HistoricoManutencaoSerializer(serializers.ModelSerializer):
    custo_total = serializers.ReadOnlyField()

    class Meta:
        model = HistoricoManutencao
        fields = '__all__'

    def validate(self, data):
        request = self.context.get('request')
        ordem = data.get(
            'ordem_servico',
            getattr(self.instance, 'ordem_servico', None),
        )
        if ordem:
            validate_company_resource(
                request.user if request else None,
                ordem.equipamento,
                'ordem_servico',
            )
        return data
