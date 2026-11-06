"""Cenários didáticos passam pela ingestão e pelos mesmos serviços operacionais."""
from datetime import timedelta
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts.models import Empresa
from ativos.models import Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico
from .models import Sensor, Telemetria, TrendConfig, TrendDemo
from .trend_analysis import analyze_sensor_trend

INTERVAL_SECONDS = 10
VALUES = {
    'aumento': [40, 42, 44, 46, 48, 50, 52],
    'limite': [60, 68, 76, 84, 92, 100, 108],
    'recuperacao': [40] * 7,
    'estavel': [40] * 7,
    'pico': [40, 40, 40, 40, 40, 40, 65],
}


def snapshot(demo):
    return {
        'id': str(demo.pk), 'cenario': demo.cenario, 'status': demo.status,
        'passo': demo.passo + 1, 'total_passos': 7, 'intervalo_segundos': INTERVAL_SECONDS,
        'proxima_leitura_em': (demo.ultima_leitura_em + timedelta(seconds=INTERVAL_SECONDS)).isoformat(),
        'sensor_id': demo.sensor_id, 'equipamento_id': demo.sensor.equipamento_id,
        'empresa_id': demo.sensor.equipamento.empresa_id,
        'analysis': analyze_sensor_trend(demo.sensor_id),
        'alertas': list(Alerta.objects.filter(sensor_id=demo.sensor_id).order_by('-pk').values(
            'id', 'origem', 'nivel', 'status', 'descricao', 'ordem_servico_id', 'data_normalizacao')[:20]),
        'ordens': list(OrdemServico.objects.filter(sensor_origem_id=demo.sensor_id).order_by('-pk').values(
            'id', 'tipo_os', 'status', 'prioridade', 'titulo')[:20]),
    }


@transaction.atomic
def create_demo(owner, empresa_id, cenario='aumento'):
    if cenario not in VALUES:
        raise ValidationError({'cenario': 'Cenário inválido.'})
    type(owner).objects.select_for_update().get(pk=owner.pk)
    empresa = Empresa.objects.filter(pk=empresa_id).first()
    if empresa is None:
        raise ValidationError({'empresa': 'Selecione uma empresa existente para a demonstração.'})
    # Uma execução por administrador. Nova demonstração preserva o histórico anterior.
    TrendDemo.objects.filter(owner=owner, status='executando').update(status='parado')
    equipamento = Equipamento.objects.create(
        empresa=empresa, nome='[DEMO] Motor de apresentação', tipo='motor_eletrico',
        numero_serie=f'DEMO-{uuid4()}', criticidade='C',
        descricao='Dados sintéticos para demonstração de tendências; não representa um ativo real.',
    )
    sensor = Sensor.objects.create(equipamento=equipamento, nome='[DEMO] Temperatura',
                                   tipo='temperatura', unidade_medida='°C', limite_alerta=100)
    TrendConfig.objects.create(sensor=sensor, periodo_horas=1, num_leituras=7,
                               minimo_leituras=7, duracao_minima_minutos=1,
                               sensibilidade='media', direcao_alerta='crescente')
    reading = Telemetria.objects.create(sensor=sensor, valor=VALUES[cenario][0])
    demo = TrendDemo.objects.create(owner=owner, sensor=sensor, cenario=cenario,
                                    ultima_leitura_em=reading.timestamp)
    return snapshot(demo)


@transaction.atomic
def update_demo(owner, demo_id, action, cenario=None):
    from django.shortcuts import get_object_or_404
    # Bloqueio inclui checagem de cadência e ingestão: ticks repetidos não duplicam passos.
    demo = get_object_or_404(TrendDemo.objects.select_for_update(), pk=demo_id, owner=owner)
    now = timezone.now()
    if action == 'parar':
        demo.status = 'parado'
        demo.save(update_fields=['status'])
    elif action == 'fase':
        if now - demo.criado_em > timedelta(minutes=30):
            raise ValidationError({'detail': 'Esta demonstração expirou. Inicie uma nova demonstração.'})
        if cenario not in VALUES:
            raise ValidationError({'cenario': 'Cenário inválido.'})
        if demo.status == 'executando':
            raise ValidationError({'detail': 'Conclua ou pare a fase atual antes de começar outra.'})
        demo.cenario, demo.passo, demo.status = cenario, 0, 'executando'
        reading = Telemetria.objects.create(sensor=demo.sensor, valor=VALUES[cenario][0])
        demo.ultima_leitura_em = reading.timestamp
        demo.save()
    elif action == 'avancar':
        if now - demo.criado_em > timedelta(minutes=30):
            demo.status = 'parado'
            demo.save(update_fields=['status'])
        elif demo.status == 'executando' and now >= demo.ultima_leitura_em + timedelta(seconds=INTERVAL_SECONDS):
            demo.passo += 1
            reading = Telemetria.objects.create(sensor=demo.sensor, valor=VALUES[demo.cenario][demo.passo])
            demo.ultima_leitura_em = reading.timestamp
            if demo.passo == 6:
                demo.status = 'concluido'
            demo.save()
    else:
        raise ValidationError({'acao': 'Ação inválida.'})
    return snapshot(demo)
