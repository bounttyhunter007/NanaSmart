"""Detecção determinística de tendências persistentes; projeções não preveem falhas."""
from datetime import timedelta
import math

from django.utils import timezone
from .models import Sensor, Telemetria, TrendConfig


CONFIG_FIELDS = (
    'periodo_horas', 'num_leituras', 'minimo_leituras', 'duracao_minima_minutos',
    'persistencia_minima', 'r2_minimo', 'direcao_alerta', 'sensibilidade', 'ativo',
    'antecedencia_os_minutos',
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


def _select_sample(rows, maximum, minimum_minutes):
    """Preserva cobertura temporal com memória limitada, mesmo em coleta rápida.

    As últimas N leituras continuam sendo preferidas. Se não cobrem a duração
    mínima, estendemos só até esse tempo e distribuímos N observações reais.
    Estatísticas de TODAS as observações percorridas impedem que a seleção
    esconda oscilações ou picos e confirme uma tendência artificial.
    """
    recent, buckets = [], {}
    latest = previous_stamp = previous_value = None
    count = rises = falls = 0
    mean_x = mean_y = sxx = syy = sxy = 0.0
    duration_seconds = minimum_minutes * 60
    for row in rows.iterator(chunk_size=500):
        stamp, value = row['timestamp'], row['valor']
        if value is None or not math.isfinite(value) or stamp == previous_stamp:
            continue
        if latest is None:
            latest = stamp
        seconds = (latest - stamp).total_seconds()
        if previous_value is not None:
            # Percurso do mais recente para o mais antigo.
            rises += previous_value > value
            falls += previous_value < value
        previous_stamp, previous_value = stamp, value
        count += 1
        x = -seconds / 3600
        dx, dy = x - mean_x, value - mean_y
        mean_x += dx / count
        mean_y += dy / count
        sxx += dx * (x - mean_x)
        syy += dy * (value - mean_y)
        sxy += dx * (value - mean_y)
        if len(recent) < maximum:
            recent.append((stamp, float(value)))
        bucket = min(maximum - 1, int(seconds * (maximum - 1) / duration_seconds))
        buckets.setdefault(bucket, (stamp, float(value)))
        if len(recent) == maximum and seconds >= duration_seconds:
            break
    distributed = bool(recent and (recent[0][0] - recent[-1][0]).total_seconds() < duration_seconds
                       and latest and (latest - previous_stamp).total_seconds() >= duration_seconds)
    selected = recent
    if distributed:
        candidates = dict(recent + list(buckets.values()) + [(previous_stamp, float(previous_value))])
        ordered = sorted(candidates)
        start, end = ordered[0], ordered[-1]
        chosen = {start, end}
        for index in range(1, maximum - 1):
            target = start + (end - start) * (index / (maximum - 1))
            chosen.add(min(ordered, key=lambda stamp: abs((stamp - target).total_seconds())))
        # Intervalos irregulares podem selecionar o mesmo ponto duas vezes.
        for stamp in reversed(ordered):
            if len(chosen) == maximum:
                break
            chosen.add(stamp)
        selected = [(stamp, candidates[stamp]) for stamp in chosen]
    stats = {'count': count, 'mean_x': mean_x, 'mean_y': mean_y,
             'sxx': sxx, 'syy': syy, 'sxy': sxy, 'rises': rises, 'falls': falls,
             'duration_minutes': (latest - previous_stamp).total_seconds() / 60 if latest else 0}
    return sorted(selected), distributed, stats


def analyze_sensor_trend(sensor_id):
    """Analisa sem gravar alertas; informa qualidade, critérios e evidências."""
    sensor = Sensor.objects.select_related('equipamento__localizacao').filter(pk=sensor_id, ativo=True).first()
    if sensor is None:
        return None
    config = get_effective_config(sensor)
    now = timezone.now()
    latest = Telemetria.objects.filter(sensor=sensor, timestamp__lte=now).order_by(
        '-timestamp', '-pk').values('id', 'valor', 'timestamp').first()
    latest_reading = (
        {**latest, 'timestamp': latest['timestamp'].isoformat()}
        if latest and latest['valor'] is not None and math.isfinite(latest['valor']) else None
    )
    result = {
        'sensor_id': sensor.id, 'sensor_info': _sensor_info(sensor),
        'latest_reading': latest_reading,
        'direction': 'stable', 'slope': 0.0, 'slope_per_hour': 0.0,
        'projected_breach_hours': None, 'projected_breach_minutes': None, 'risk_level': 'baixo',
        'current_value': None, 'limite_operacional': sensor.limite_alerta,
        'readings_summary': [], 'readings_count': 0, 'config_used': config,
        'regression_line': None, 'projected_breach_at': None,
        'insufficient_data': False, 'analysis_enabled': config['ativo'],
        'data_quality': 'disabled', 'analysis_window_hours': config['periodo_horas'],
        'sample_duration_minutes': 0.0, 'r_squared': None, 'persistence_ratio': 0.0,
        'sample_selection': 'recent', 'source_readings_count': 0,
        'source_duration_minutes': 0.0,
        'source_r_squared': None, 'source_persistence_ratio': None,
        'is_anomalous': False, 'intervention_recommended': False,
        'intervention_reason': 'disabled' if not config['ativo'] else 'insufficient_data',
        'method_version': 'linear-persistent-upper-limit-v2',
        'checks': [{'label': 'Análise ativa', 'passed': config['ativo']}],
        'threshold_per_hour': None,
        'analyzed_at': now.isoformat(), **_operational_context(sensor.id),
    }
    if not config['ativo']:
        return result

    # Em cada timestamp vence o maior id válido, sem consumir cota com duplicatas.
    rows = Telemetria.objects.filter(
        sensor=sensor, timestamp__gte=now - timedelta(hours=config['periodo_horas']),
        timestamp__lte=now,
    ).order_by('-timestamp', '-id').values('valor', 'timestamp')
    readings, distributed, source = _select_sample(
        rows, config['num_leituras'], config['duracao_minima_minutos'],
    )
    result.update(
        readings_summary=[{'valor': value, 'timestamp': stamp.isoformat()} for stamp, value in readings],
        readings_count=len(readings),
        sample_selection='time_distributed' if distributed else 'recent',
        source_readings_count=source['count'],
        source_duration_minutes=round(source['duration_minutes'], 4),
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
    source_ok = True
    if distributed:
        # Avalia o ajuste exibido também contra todos os pontos originais.
        fitted_at_latest = mean_y + slope * (xs[-1] - mean_x)
        error = (source['syy'] - 2 * slope * source['sxy'] + slope ** 2 * source['sxx']
                 + source['count'] * (source['mean_y'] - fitted_at_latest - slope * source['mean_x']) ** 2)
        source_r2 = max(0.0, min(1.0, 1 - max(0.0, error) / source['syy'])) if source['syy'] else 1.0
        source_persistence = (source['rises'] if slope > 0 else source['falls']) / (source['count'] - 1)
        source_ok = source_r2 >= config['r2_minimo'] and source_persistence >= config['persistencia_minima']
        result.update(source_r_squared=round(source_r2, 6), source_persistence_ratio=round(source_persistence, 6))
        result['checks'].append({'label': 'Consistência das leituras originais', 'passed': source_ok})
    if r_squared < config['r2_minimo'] or persistence < config['persistencia_minima'] or not source_ok:
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
    # Decisão com precisão completa; a projeção é ancorada na última medição.
    eligible = bool(anomalous and projection is not None and
                    0 < projection * 60 <= config['antecedencia_os_minutos'] and
                    projected_at and readings[-1][0] + timedelta(hours=projection) > now)
    if ys[-1] >= limit:
        reason = 'limit_reached'
    elif not anomalous:
        reason = 'no_anomaly'
    elif projection is None:
        reason = 'no_upper_limit_projection'
    elif not projected_at or readings[-1][0] + timedelta(hours=projection) <= now:
        reason = 'expired_projection'
    else:
        reason = 'within_horizon' if eligible else 'outside_horizon'
    result['checks'].extend([
        {'label': 'Previsão dentro da antecedência da O.S.', 'passed': bool(
            projection is not None and 0 < projection * 60 <= config['antecedencia_os_minutos'])},
        {'label': 'Estimativa ainda futura', 'passed': bool(
            projected_at and readings[-1][0] + timedelta(hours=projection) > now)},
    ])
    risk = _calculate_risk_level(ys[-1], limit, direction, projection, config['sensibilidade'])
    if anomalous and risk == 'baixo':
        risk = 'medio'
    result.update(
        direction=direction, slope=round(slope, 6), slope_per_hour=round(slope, 4),
        projected_breach_hours=round(projection, 2) if projection is not None else None,
        projected_breach_minutes=round(projection * 60, 2) if projection is not None else None,
        risk_level=risk, data_quality='valid', r_squared=round(r_squared, 6),
        persistence_ratio=round(persistence, 6), is_anomalous=anomalous,
        intervention_recommended=eligible, intervention_reason=reason,
        slope_full_precision=slope,
        regression_line=regression_line, projected_breach_at=projected_at,
    )
    return result


def _operational_context(sensor_id):
    from alertas.models import Alerta
    from manutencao.models import OrdemServico
    alerta = Alerta.objects.filter(sensor_id=sensor_id, origem='tendencia', status='ativo').order_by('-data_alerta').first()
    limite = Alerta.objects.filter(sensor_id=sensor_id, origem='limite', status='ativo').order_by('-pk').first()
    return {
        'active_alert_id': alerta.id if alerta else None,
        'predictive_work_order': OrdemServico.objects.filter(pk=alerta.ordem_servico_id).values('id', 'status').first() if alerta else None,
        'limit_alert': {'id': limite.pk, 'level': limite.nivel,
                        'current_level': (limite.dados_analise or {}).get('nivel_atual'),
                        'work_order': OrdemServico.objects.filter(pk=limite.ordem_servico_id).values('id', 'status').first()} if limite else None,
    }


def _sensor_info(sensor):
    return {
        'id': sensor.id, 'nome': sensor.nome, 'tipo': sensor.tipo,
        'tipo_display': sensor.get_tipo_display(), 'unidade_medida': sensor.unidade_medida,
        'limite_alerta': sensor.limite_alerta, 'equipamento_id': sensor.equipamento_id,
        'limite_alerta_baixo_pct': sensor.limite_alerta_baixo_pct,
        'limite_alerta_medio_pct': sensor.limite_alerta_medio_pct,
        'limite_alerta_critico_pct': sensor.limite_alerta_critico_pct,
        'equipamento_nome': sensor.equipamento.nome,
        'setor': getattr(getattr(sensor.equipamento, 'localizacao', None), 'setor', None),
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
