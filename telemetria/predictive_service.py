"""Orquestração determinística de alertas e OS para tendências.

O serviço não chama o Gemini: a decisão operacional é sempre calculada pelo
backend. A IA é opcional e pode explicar um alerta depois, sem bloquear este
fluxo.
"""

from django.db import transaction
from django.utils import timezone

from alertas.models import Alerta
from alertas.evidence import detection_snapshot
from .models import Sensor
from .trend_analysis import analyze_sensor_trend, _operational_context


RISK_TO_ALERT = {'baixo': 'baixo', 'medio': 'medio', 'alto': 'critico', 'critico': 'critico'}


@transaction.atomic
def sync_sensor_trend(sensor_id):
    """Atualiza o episódio de tendência do sensor de forma idempotente."""
    # Mesmo bloqueio da ingestão: inclui análise, resolução e criação, inclusive
    # quando ainda não há alerta. Evita aplicar uma análise antiga após a nova.
    sensor = Sensor.objects.select_for_update().filter(pk=sensor_id, ativo=True).first()
    if sensor is None:
        return None
    trend = analyze_sensor_trend(sensor_id)
    if not trend or not trend['analysis_enabled'] or trend.get('insufficient_data'):
        return trend

    is_relevant = trend['is_anomalous']
    event_key = f'tendencia:{sensor.id}:{trend["direction"]}'

    active = Alerta.objects.select_for_update().filter(
        sensor=sensor, origem='tendencia', status='ativo'
    )
    if not is_relevant:
        active.update(status='resolvido', data_ultima_analise=timezone.now(), data_normalizacao=timezone.now())
        trend.update(_operational_context(sensor.id))
        return trend

    # Um novo sentido é um novo episódio; o anterior fica auditável.
    active.exclude(evento_chave=event_key).update(
        status='resolvido', data_ultima_analise=timezone.now()
    )
    alerta = active.filter(evento_chave=event_key).first()
    descricao = _trend_description(sensor, trend)
    values = {
        'sensor': sensor,
        'tipo_alerta': f'Tendência de {sensor.get_tipo_display()} ({trend["direction"]})',
        'origem': 'tendencia',
        'evento_chave': event_key,
        'nivel': RISK_TO_ALERT[trend['risk_level']],
        'descricao': descricao,
        'dados_analise': trend,
        'data_ultima_analise': timezone.now(),
        'status': 'ativo',
    }
    if alerta is None:
        values['dados_deteccao'] = detection_snapshot(
            sensor, 'tendencia', values['tipo_alerta'], values['nivel'], descricao, trend,
        )
        alerta = Alerta.objects.create(equipamento=sensor.equipamento, **values)
    else:
        weights = {'baixo': 1, 'medio': 2, 'critico': 3}
        values['nivel'] = max((alerta.nivel, values['nivel']), key=weights.__getitem__)
        for field, value in values.items():
            setattr(alerta, field, value)
        alerta.save()
    trend.update(_operational_context(sensor.id))
    return trend


def _trend_description(sensor, trend):
    condition = 'aumento' if trend['direction'] == 'increasing' else 'redução'
    projection = trend.get('projected_breach_hours')
    projection_text = (
        'não foi possível estimar o tempo até o limite'
        if projection is None else f'estimativa de {projection} hora(s) até o limite'
    )
    return (
        f'O equipamento {sensor.equipamento.nome}, sensor {sensor.nome}, apresenta {condition} persistente de '
        f'{sensor.get_tipo_display().lower()} ({trend["readings_count"]} leituras). '
        f'Duração: {trend["sample_duration_minutes"]} minuto(s); '
        f'R²: {trend["r_squared"]}; persistência: {trend["persistence_ratio"]:.0%}. '
        f'Inclinação observada: {trend["slope_per_hour"]} {sensor.unidade_medida}/hora; '
        f'valor atual: {trend.get("current_value")} {sensor.unidade_medida}; '
        f'limite superior: {sensor.limite_alerta} {sensor.unidade_medida}; '
        f'{projection_text}. Trata-se de uma indicação de risco, não de garantia de falha.'
    )
