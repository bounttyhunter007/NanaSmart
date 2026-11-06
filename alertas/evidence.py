"""Evidências da abertura, independentes das próximas análises do sensor."""
from copy import deepcopy
import math


def detection_snapshot(sensor, origem, tipo_alerta, nivel, descricao, dados, leitura=None):
    if leitura is not None:
        # A evidência termina na leitura que disparou o alerta, inclusive em
        # ingestões retroativas. Empates de timestamp respeitam a ordem de entrada.
        from django.db.models import Q
        from telemetria.models import Telemetria
        rows = list(Telemetria.objects.filter(sensor=sensor).filter(
            Q(timestamp__lt=leitura.timestamp)
            | Q(timestamp=leitura.timestamp, pk__lte=leitura.pk)
        ).order_by('-timestamp', '-pk').values('id', 'valor', 'timestamp')[:50])
        readings = [dict(row, timestamp=row['timestamp'].isoformat()) for row in reversed(rows)
                    if row['valor'] is not None and math.isfinite(row['valor'])]
    else:
        readings = deepcopy(dados.get('readings_summary', []))
    analysis = deepcopy(dados)
    analysis.pop('readings_summary', None)
    return {
        'legado': False, 'origem': origem, 'tipo_alerta': tipo_alerta,
        'equipamento_id': sensor.equipamento_id, 'equipamento_nome': sensor.equipamento.nome,
        'sensor_id': sensor.pk, 'sensor_nome': sensor.nome,
        'unidade_medida': sensor.unidade_medida, 'nivel': nivel, 'descricao': descricao,
        'limite_operacional': sensor.limite_alerta,
        'leituras': readings, 'analise': analysis,
    }
