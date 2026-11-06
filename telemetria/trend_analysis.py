"""Detecção determinística de tendências persistentes; projeções não preveem falhas."""
from datetime import timedelta
import math

from django.utils import timezone
from .models import Sensor, Telemetria, TrendConfig


CONFIG_FIELDS = (
    'periodo_horas', 'num_leituras', 'minimo_leituras', 'duracao_minima_minutos',
    'persistencia_minima', 'r2_minimo', 'direcao_alerta', 'sensibilidade', 'ativo',
)


def get_effective_config(sensor):
    """Config específica > global mais recente > defaults, inclusive quando inativa."""
    config = TrendConfig.objects.filter(sensor=sensor).first()
    is_custom = config is not None
    if config is None:
        config = TrendConfig.objects.filter(sensor__isnull=True).order_by('-pk').first()
    source = 'sensor' if is_custom else ('global' if config else 'padrao')
    config = config or TrendConfig()
    return {**{field: getattr(config, field) for field in CONFIG_FIELDS},
            'is_custom': is_custom, 'source': source}


def _sensitivity_threshold(sensibilidade):
    return {'alta': 0.005, 'media': 0.02, 'baixa': 0.05}[sensibilidade]


def analyze_sensor_trend(sensor_id):
    """Analisa sem gravar alertas; informa qualidade, critérios e evidências."""
    sensor = Sensor.objects.select_related('equipamento').filter(pk=sensor_id, ativo=True).first()
    if sensor is None:
        return None
    config = get_effective_config(sensor)
    now = timezone.now()
    result = {
        'sensor_id': sensor.id, 'sensor_info': _sensor_info(sensor),
        'direction': 'stable', 'slope': 0.0, 'slope_per_hour': 0.0,
        'projected_breach_hours': None, 'projected_breach_minutes': None, 'risk_level': 'baixo',
        'current_value': None, 'limite_operacional': sensor.limite_alerta,
        'readings_summary': [], 'readings_count': 0, 'config_used': config,
        'regression_line': None, 'projected_breach_at': None,
        'insufficient_data': False, 'analysis_enabled': config['ativo'],
        'data_quality': 'disabled', 'analysis_window_hours': config['periodo_horas'],
        'sample_duration_minutes': 0.0, 'r_squared': None, 'persistence_ratio': 0.0,
        'is_anomalous': False, 'intervention_recommended': False,
        'checks': [{'label': 'Análise ativa', 'passed': config['ativo']}],
        'threshold_per_hour': None,
        'analyzed_at': now.isoformat(), **_operational_context(sensor.id),
    }
    if not config['ativo']:
        return result

    # Percorre até obter o máximo de amostras válidas, sem deixar duplicatas
    # consumirem a cota. Em cada timestamp vence o maior id válido.
    rows = Telemetria.objects.filter(
        sensor=sensor, timestamp__gte=now - timedelta(hours=config['periodo_horas']),
        timestamp__lte=now,
    ).order_by('-timestamp', '-id').values('valor', 'timestamp')
    unique = {}
    for reading in rows.iterator(chunk_size=500):
        value = reading['valor']
        if value is None or not math.isfinite(value):
            continue
        unique.setdefault(reading['timestamp'], float(value))
        if len(unique) == config['num_leituras']:
            break
    readings = sorted(unique.items())
    result.update(
        readings_summary=[{'valor': value, 'timestamp': stamp.isoformat()} for stamp, value in readings],
        readings_count=len(readings),
    )
    duration = (readings[-1][0] - readings[0][0]).total_seconds() / 60 if readings else 0
    result['sample_duration_minutes'] = round(duration, 4)
    if readings:
        result['current_value'] = readings[-1][1]
    result['checks'].extend([
        {'label': 'Quantidade mínima de leituras', 'passed': len(readings) >= config['minimo_leituras']},
        {'label': 'Tempo mínimo observado', 'passed': duration >= config['duracao_minima_minutos']},
    ])
    if len(readings) < config['minimo_leituras'] or duration < config['duracao_minima_minutos']:
        result.update(insufficient_data=True, data_quality='insufficient')
        return result

    xs = [(stamp - readings[0][0]).total_seconds() / 3600 for stamp, _ in readings]
    ys = [value for _, value in readings]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    # Forma centrada evita cancelamento numérico de n*sum(x²) - sum(x)².
    sxx = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sxx
    total = sum((y - mean_y) ** 2 for y in ys)
    residual = sum((y - (mean_y + slope * (x - mean_x))) ** 2 for x, y in zip(xs, ys))
    r_squared = max(0.0, min(1.0, 1 - residual / total)) if total else 1.0
    limit = sensor.limite_alerta
    threshold = _sensitivity_threshold(config['sensibilidade']) * (abs(limit) if limit else 1)
    direction = 'increasing' if slope > threshold else ('decreasing' if slope < -threshold else 'stable')
    persistence = sum((b - a) * slope > 0 for a, b in zip(ys, ys[1:])) / (len(ys) - 1)
    if r_squared < config['r2_minimo'] or persistence < config['persistencia_minima']:
        direction = 'stable'

    abnormal_directions = {
        'crescente': ('increasing',), 'decrescente': ('decreasing',),
        'ambas': ('increasing', 'decreasing'),
    }[config['direcao_alerta']]
    anomalous = direction in abnormal_directions
    result['threshold_per_hour'] = threshold
    result['checks'].extend([
        {'label': 'Ritmo acima da sensibilidade', 'passed': abs(slope) > threshold},
        {'label': 'Movimento consistente (R²)', 'passed': r_squared >= config['r2_minimo']},
        {'label': 'Movimento persistente', 'passed': persistence >= config['persistencia_minima']},
        {'label': 'Sentido configurado como anormal', 'passed': anomalous},
    ])
    projection = None
    # O cadastro modela somente limite superior. Quedas nunca projetam esse limite.
    if direction == 'increasing' and math.isfinite(limit):
        projection = max(0.0, (limit - ys[-1]) / slope)
    # Presentation only: keep the fitted line inside the observed sample.
    # The existing projection starts at the LAST measurement, not the query time.
    regression_line = [
        {'timestamp': stamp.isoformat(), 'valor': mean_y + slope * (x - mean_x)}
        for stamp, x in ((readings[0][0], xs[0]), (readings[-1][0], xs[-1]))
    ]
    projected_at = None
    if projection is not None and projection > 0 and math.isfinite(projection):
        try:
            projected_at = (readings[-1][0] + timedelta(hours=projection)).isoformat()
        except OverflowError:
            pass  # An unrepresentable date must not break the analysis.
    risk = _calculate_risk_level(ys[-1], limit, direction, projection, config['sensibilidade'])
    if anomalous and risk == 'baixo':
        risk = 'medio'
    result.update(
        direction=direction, slope=round(slope, 6), slope_per_hour=round(slope, 4),
        projected_breach_hours=round(projection, 2) if projection is not None else None,
        projected_breach_minutes=round(projection * 60, 2) if projection is not None else None,
        risk_level=risk, data_quality='valid', r_squared=round(r_squared, 6),
        persistence_ratio=round(persistence, 6), is_anomalous=anomalous,
        intervention_recommended=anomalous,
        regression_line=regression_line, projected_breach_at=projected_at,
    )
    return result


def _operational_context(sensor_id):
    from alertas.models import Alerta
    from manutencao.models import OrdemServico
    alerta = Alerta.objects.filter(sensor_id=sensor_id, origem='tendencia', status='ativo').order_by('-data_alerta').first()
    if alerta is None:
        return {'active_alert_id': None, 'predictive_work_order': None}
    return {'active_alert_id': alerta.id,
            'predictive_work_order': OrdemServico.objects.filter(alerta_origem=alerta).values('id', 'status').first()}


def _sensor_info(sensor):
    return {
        'id': sensor.id, 'nome': sensor.nome, 'tipo': sensor.tipo,
        'tipo_display': sensor.get_tipo_display(), 'unidade_medida': sensor.unidade_medida,
        'limite_alerta': sensor.limite_alerta, 'equipamento_id': sensor.equipamento_id,
        'equipamento_nome': sensor.equipamento.nome,
    }


def _calculate_risk_level(valor_atual, limite, direction, breach_hours, sensibilidade):
    if valor_atual >= limite:
        return 'critico'
    if direction == 'increasing' and breach_hours is not None:
        if breach_hours <= 2:
            return 'critico'
        if breach_hours <= 8:
            return 'alto'
        if breach_hours <= 24:
            return 'medio'
    if limite > 0:
        if valor_atual >= limite * 0.85:
            return 'alto'
        if valor_atual >= limite * 0.70:
            return 'medio'
    return 'baixo'


def get_all_sensor_trends(user, only_atypical=False, empresa_id=None):
    sensors = Sensor.objects.filter(ativo=True).select_related('equipamento')
    if user.tipo_usuario != 'admin':
        if not user.empresa:
            return []
        sensors = sensors.filter(equipamento__empresa=user.empresa)
    if empresa_id:
        try:
            sensors = sensors.filter(equipamento__empresa_id=int(empresa_id))
        except (TypeError, ValueError):
            return []
    results = []
    for sensor in sensors:
        trend = analyze_sensor_trend(sensor.id)
        if trend is None:
            continue
        if only_atypical and (not trend['analysis_enabled'] or trend['insufficient_data'] or
                              (trend['direction'] == 'stable' and trend['risk_level'] == 'baixo')):
            continue
        results.append(trend)
    risk_order = {'critico': 0, 'alto': 1, 'medio': 2, 'baixo': 3}
    results.sort(key=lambda trend: risk_order[trend['risk_level']])
    return results
