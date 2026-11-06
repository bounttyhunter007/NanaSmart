from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count
from ativos.models import Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico, HistoricoManutencao
from telemetria.models import Sensor, Telemetria
from manutencao.dashboards.views import KpiService


def get_user_equipment_queryset(user):
    if user.tipo_usuario == 'admin':
        return Equipamento.objects.select_related('localizacao', 'empresa')

    if not user.empresa:
        return Equipamento.objects.none()

    return Equipamento.objects.filter(empresa=user.empresa).select_related('localizacao')


def get_open_orders(user):
    equipamentos = get_user_equipment_queryset(user)
    return OrdemServico.objects.filter(
        equipamento__in=equipamentos,
        status__in=['pendente', 'andamento']
    ).select_related('equipamento', 'responsavel')


def get_unassigned_orders(user):
    return get_open_orders(user).filter(responsavel__isnull=True)


def get_assigned_orders(user):
    return get_open_orders(user).filter(responsavel=user)


def get_active_alerts(user):
    equipamentos = get_user_equipment_queryset(user)
    return Alerta.objects.filter(equipamento__in=equipamentos, status='ativo').select_related('equipamento')


def get_recent_telemetry(user, limit=5):
    equipamentos = get_user_equipment_queryset(user)
    sensores = Sensor.objects.filter(equipamento__in=equipamentos, ativo=True).select_related('equipamento')
    resumo = []
    for sensor in sensores[:limit]:
        ultima_leitura = Telemetria.objects.filter(sensor=sensor).order_by('-timestamp').first()
        if not ultima_leitura:
            continue
        resumo.append(
            f"- Sensor {sensor.nome} ({sensor.get_tipo_display()}) do equipamento '{sensor.equipamento.nome}': "
            f"valor {ultima_leitura.valor}{sensor.unidade_medida} às {ultima_leitura.timestamp.strftime('%d/%m/%Y %H:%M')} "
            f"(limite crítico {sensor.limite_alerta}{sensor.unidade_medida})"
        )
    return resumo


def get_recent_alerts(user):
    return Alerta.objects.filter(
        equipamento__in=get_user_equipment_queryset(user),
        data_alerta__gte=timezone.now() - timedelta(hours=24), data_alerta__lte=timezone.now(),
    ).select_related('equipamento').order_by('-data_alerta', '-pk')


def build_alert_summary(alerts, limit=5):
    summary = []
    for alerta in alerts[:limit]:
        evidence = alerta.dados_deteccao or {}
        normalization = (f"normalização detectada em {alerta.data_normalizacao.isoformat()}"
                         if alerta.data_normalizacao else 'sem registro de normalização; consultar leituras atuais')
        summary.append(
            f"- Ocorrência histórica #{alerta.pk} [{alerta.nivel.upper()} máximo] "
            f"{alerta.tipo_alerta} no equipamento '{alerta.equipamento.nome}': "
            f"{evidence.get('descricao', alerta.descricao)} "
            f"(registrada em {alerta.data_alerta.isoformat()}; {normalization}; "
            f"O.S. vinculada: {alerta.ordem_servico_id or 'não disponível'})."
        )
    return summary


def build_order_summary(orders, limit=5):
    summary = []
    for ordem in orders[:limit]:
        responsavel = ordem.responsavel.username if ordem.responsavel else 'Não designado'
        summary.append(
            f"- #{ordem.id} '{ordem.titulo}' [{ordem.tipo_os.upper()} / Prioridade: {(ordem.prioridade or 'A definir').upper()}] - "
            f"Status: {ordem.status} - Equipamento: {ordem.equipamento.nome} - Responsável: {responsavel}"
        )
    return summary


def build_equipment_kpi_summary(user, max_equip=5):
    equipamentos = get_user_equipment_queryset(user)
    os_base = OrdemServico.objects.filter(
        status='concluida',
        data_conclusao__isnull=False,
        equipamento__in=equipamentos
    )

    summary = []
    for equipamento in equipamentos[:max_equip]:
        kpi = KpiService.calcular_kpi(equipamento, os_base)
        status = equipamento.status.upper()
        local = getattr(getattr(equipamento, 'localizacao', None), 'setor', 'Não informado')
        bloco = (
            f"- {kpi['equipamento']} (ID: {kpi['equipamento_id']}, Status: {status}, Local: {local}) -> "
            f"MTBF: {kpi['mtbf_hours']}h | MTTR: {kpi['mttr_hours']}h | "
            f"Disponibilidade: {kpi['disponibilidade_porcentagem'] if kpi['disponibilidade_porcentagem'] is not None else 'Sem histórico'} | "
            f"Manutenções: {kpi['total_manutencoes']}"
        )
        summary.append(bloco)
    return summary


def get_financial_summary(user, max_items=5):
    equipamentos = get_user_equipment_queryset(user)
    historicos = HistoricoManutencao.objects.filter(
        ordem_servico__equipamento__in=equipamentos,
        ordem_servico__status='concluida',
        ordem_servico__data_conclusao__isnull=False
    ).select_related('ordem_servico', 'ordem_servico__equipamento')

    total_pecas = historicos.aggregate(total=Sum('custo_pecas'))['total'] or 0
    total_mao = historicos.aggregate(total=Sum('custo_mao_de_obra'))['total'] or 0
    total_cost = float(total_pecas + total_mao)
    total_os = historicos.count()
    average_cost = round(total_cost / total_os, 2) if total_os else 0.0

    equipamentos_custos = {}
    for item in historicos:
        nome = item.ordem_servico.equipamento.nome if item.ordem_servico.equipamento else 'Não informado'
        equipamentos_custos.setdefault(nome, 0.0)
        equipamentos_custos[nome] += float(item.custo_pecas + item.custo_mao_de_obra)

    top_equipamentos = sorted(
        equipamentos_custos.items(),
        key=lambda pair: pair[1],
        reverse=True
    )[:max_items]

    top_blocks = [f"- {nome}: R$ {valor:.2f}" for nome, valor in top_equipamentos]

    return {
        'total_cost': round(total_cost, 2),
        'average_cost_per_os': average_cost,
        'completed_orders': total_os,
        'top_equipment_costs': top_blocks,
    }


def build_base_context(user):
    equipamentos = get_user_equipment_queryset(user)
    alerts = get_recent_alerts(user)
    open_orders = get_open_orders(user)
    assigned_orders = get_assigned_orders(user)
    unassigned_orders = get_unassigned_orders(user)
    telemetry = get_recent_telemetry(user)
    equipment_kpis = build_equipment_kpi_summary(user)

    return {
        'company_name': user.empresa.nome if getattr(user, 'empresa', None) else 'Sem empresa vinculada',
        'total_equipment': equipamentos.count(),
        'active_equipment': equipamentos.filter(status='ativo').count(),
        'maintenance_equipment': equipamentos.filter(status='manutencao').count(),
        'inactive_equipment': equipamentos.filter(status='inativo').count(),
        'alerts': alerts,
        'open_orders': open_orders,
        'assigned_orders': assigned_orders,
        'unassigned_orders': unassigned_orders,
        'telemetry': telemetry,
        'equipment_kpis': equipment_kpis,
        'alert_summary': build_alert_summary(alerts),
        'open_order_summary': build_order_summary(open_orders),
        'assigned_order_summary': build_order_summary(assigned_orders),
        'unassigned_order_summary': build_order_summary(unassigned_orders),
    }
