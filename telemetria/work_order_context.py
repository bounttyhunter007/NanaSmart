"""Resumo de atendimento para a tela; não participa da decisão preditiva."""
from django.db.models import Case, Count, F, IntegerField, Q, When, Window
from django.db.models.functions import Coalesce, RowNumber

from manutencao.visibility import visible_work_orders


def attach_predictive_order_summaries(trends, user):
    """Duas consultas em lote, sem descrições nem evidências das ordens."""
    by_sensor = {trend['sensor_id']: trend for trend in trends}
    for trend in trends:
        trend['predictive_orders_summary'] = {'total': 0, 'open_count': 0, 'primary_order': None}
    if not by_sensor:
        return trends
    orders = visible_work_orders(user).filter(tipo_os='preditiva').annotate(
        context_sensor_id=Coalesce('sensor_origem_id', 'alerta_origem__sensor_id'),
    ).filter(context_sensor_id__in=by_sensor)
    opened = Q(status__in=('pendente', 'andamento'))
    counts = orders.order_by().values('context_sensor_id').annotate(
        total=Count('pk'), open_count=Count('pk', filter=opened),
    )
    for row in counts:
        by_sensor[row['context_sensor_id']]['predictive_orders_summary'].update(
            total=row['total'], open_count=row['open_count'],
        )
    first = orders.annotate(context_rank=Window(
        expression=RowNumber(), partition_by=[F('context_sensor_id')],
        order_by=[Case(When(opened, then=0), default=1, output_field=IntegerField()),
                  F('data_abertura').desc(), F('pk').desc()],
    )).filter(context_rank=1).order_by().values('context_sensor_id', 'id', 'titulo', 'status', 'data_abertura')
    for row in first:
        sensor_id = row.pop('context_sensor_id')
        row['data_abertura'] = row['data_abertura'].isoformat()
        by_sensor[sensor_id]['predictive_orders_summary']['primary_order'] = row
    return trends
