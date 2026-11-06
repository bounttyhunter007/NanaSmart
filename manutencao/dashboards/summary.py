"""Read models for the home screen; counts never depend on a paginated list."""
from datetime import timedelta

from django.db.models import Case, When, IntegerField, Count, Sum, Q
from django.utils import timezone
from rest_framework import serializers

from accounts.models import Empresa
from ativos.models import Equipamento
from alertas.models import Alerta
from alertas.serializers import AlertaSerializer
from manutencao.ordering import prioridade_rank
from manutencao.models import OrdemServico, HistoricoManutencao
from manutencao.serializers import OrdemServicoSerializer


class SummaryParams(serializers.Serializer):
    empresa_id = serializers.IntegerField(min_value=1, required=False)
    equipamento_id = serializers.IntegerField(min_value=1, required=False)
    setor = serializers.CharField(required=False)
    incluir_desempenho = serializers.BooleanField(default=True)
    dias = serializers.IntegerField(min_value=1, required=False)


def build_summary(request, kpi_service):
    params = SummaryParams(data=request.query_params)
    params.is_valid(raise_exception=True)
    p, user = params.validated_data, request.user
    equipments = Equipamento.objects.select_related('localizacao').order_by('nome', 'pk')
    orders = OrdemServico.objects.select_related('equipamento', 'responsavel')
    if user.tipo_usuario == 'admin':
        if p.get('empresa_id'):
            equipments = equipments.filter(empresa_id=p['empresa_id'])
    else:
        if not user.empresa_id:
            raise serializers.ValidationError({'error': 'Usuário sem empresa vinculada.'})
        equipments = equipments.filter(empresa_id=user.empresa_id)
        if user.tipo_usuario == 'tecnico':
            orders = orders.filter(Q(responsavel=user) | Q(responsavel__isnull=True))
            equipments = equipments.filter(pk__in=orders.values('equipamento_id'))

    options = [{'id': e.pk, 'nome': e.nome, 'status': e.status,
                'setor': getattr(getattr(e, 'localizacao', None), 'setor', ''),
                'empresa': e.empresa_id} for e in equipments]
    if p.get('setor'):
        equipments = equipments.filter(localizacao__setor=p['setor'])
    if p.get('equipamento_id'):
        equipments = equipments.filter(pk=p['equipamento_id'])
    orders = orders.filter(equipamento__in=equipments)
    opened = orders.filter(status__in=['pendente', 'andamento'])
    alerts = Alerta.objects.filter(equipamento__in=equipments).select_related(
        'equipamento', 'sensor', 'ordem_servico', 'ordem_servico_preditiva')
    active = alerts.filter(status='ativo')
    now = timezone.now()
    recent = alerts.filter(data_alerta__gte=now - timedelta(hours=24), data_alerta__lte=now)

    def counts(qs, field, choices):
        result = dict.fromkeys(choices, 0)
        for row in qs.order_by().values(field).annotate(total=Count('pk')):
            result[row[field]] = row['total']
        return result

    equipment_counts = counts(equipments, 'status', ['ativo', 'manutencao', 'inativo'])
    equipment_counts['total'] = sum(equipment_counts.values())
    active_counts = counts(active, 'nivel', ['baixo', 'medio', 'critico'])
    active_counts['total'] = sum(active_counts.values())
    recent_counts = counts(recent, 'nivel', ['baixo', 'medio', 'critico'])
    recent_counts['total'] = sum(recent_counts.values())
    priority = prioridade_rank()
    severity = Case(When(nivel='critico', then=0), When(nivel='medio', then=1),
                    default=2, output_field=IntegerField())

    def order_list(qs, personal=False):
        qs = qs.annotate(priority_rank=priority)
        fields = ['priority_rank', 'data_abertura', 'pk']
        if personal:
            qs = qs.annotate(work_rank=Case(When(status='andamento', then=0), default=1,
                                          output_field=IntegerField()))
            fields.insert(0, 'work_rank')
        items = list(qs.order_by(*fields)[:5])
        data = OrdemServicoSerializer(items, many=True).data
        for item, order in zip(data, items):
            item['equipamento_nome'] = order.equipamento.nome
            item['responsavel_nome'] = (order.responsavel.get_full_name() or order.responsavel.username) if order.responsavel else None
        return data

    free = opened.filter(responsavel__isnull=True)
    mine = opened.filter(responsavel=user)
    result = {
        'atualizado_em': now,
        'empresa_atual': {'id': user.empresa_id, 'nome': user.empresa.nome} if user.empresa_id else None,
        'opcoes_equipamentos': options,
        'setores': sorted({e['setor'] for e in options if e['setor']}),
        'resumo_status': equipment_counts,
        'alertas_ativos': active_counts,
        'alertas_24h': recent_counts,
        'alertas_recentes': AlertaSerializer(recent.order_by('-data_alerta', '-pk')[:6], many=True).data,
        'alertas_prioritarios': AlertaSerializer(active.annotate(severity_rank=severity).order_by(
            'severity_rank', '-data_alerta', '-pk')[:5], many=True).data,
        'os_abertas': opened.count(),
        'ordens_abertas': opened.count(),
        'ordens_sem_tecnico': free.count(),
        'resumo_ordens': counts(orders, 'status', [s for s, _ in OrdemServico.STATUS_CHOICES]),
        'ordens_prioritarias': order_list(opened),
    }
    if user.tipo_usuario == 'tecnico':
        result.update({
            'minhas_ordens': mine.count(),
            'minhas_pendentes': mine.filter(status='pendente').count(),
            'minhas_em_andamento': mine.filter(status='andamento').count(),
            'minhas_ordens_prioritarias': order_list(mine, personal=True),
            'ordens_disponiveis': order_list(free),
            'total_equipamentos': equipment_counts['total'],
            'equipamentos': options,
            # Preserve the legacy representation of recent orders.
            'ordens_recentes': [{'id': o.pk, 'titulo': o.titulo, 'status': o.status,
                                'equipamento': o.equipamento.nome,
                                'responsavel': o.responsavel.username if o.responsavel else None,
                                'data_abertura': o.data_abertura}
                               for o in orders.order_by('-data_abertura', '-pk')[:5]],
        })
        return result

    if user.tipo_usuario == 'admin' and not p.get('empresa_id'):
        # Separate aggregations avoid multiplying counts through unrelated joins.
        eq_counts = {r['empresa_id']: r for r in equipments.order_by().values('empresa_id').annotate(
            total=Count('pk'), manutencao=Count('pk', filter=Q(status='manutencao')))}
        alert_counts = dict(active.filter(nivel='critico').order_by().values(
            'equipamento__empresa_id').annotate(total=Count('pk')).values_list('equipamento__empresa_id', 'total'))
        order_counts = {r['equipamento__empresa_id']: r for r in opened.order_by().values(
            'equipamento__empresa_id').annotate(total=Count('pk'), livres=Count('pk', filter=Q(responsavel__isnull=True)))}
        companies = []
        for company in Empresa.objects.all():
            eq = eq_counts.get(company.pk, {})
            work = order_counts.get(company.pk, {})
            companies.append({'id': company.pk, 'nome': company.nome,
                              'equipamentos': eq.get('total', 0), 'em_manutencao': eq.get('manutencao', 0),
                              'alertas_criticos': alert_counts.get(company.pk, 0),
                              'ordens_abertas': work.get('total', 0), 'sem_responsavel': work.get('livres', 0)})
        companies.sort(key=lambda c: (-c['alertas_criticos'], -c['sem_responsavel'], c['nome'].casefold()))
        result['empresas'] = companies
        result['total_empresas'] = len(companies)
        result['empresas_com_alertas_criticos'] = sum(c['alertas_criticos'] > 0 for c in companies)

    if not p['incluir_desempenho']:
        return result
    completed = orders.filter(status='concluida', data_conclusao__isnull=False)
    if p.get('dias'):
        completed = completed.filter(data_abertura__gte=now - timedelta(days=p['dias']))
    items = [kpi_service.calcular_kpi(e, completed) for e in equipments]

    def average(values, default=0):
        return round(sum(values) / len(values), 2) if values else default

    mttr = [k['mttr_hours'] for k in items if k['total_manutencoes'] > 0]
    mtbf = [k['mtbf_hours'] for k in items if k['amostras_mtbf'] > 0]
    availability = [k['disponibilidade_porcentagem'] for k in items if k['amostras_mtbf'] > 0
                    and k['disponibilidade_porcentagem'] is not None]
    cost = round(sum(k['custo_total_manutencao'] for k in items), 2)
    result['kpis_globais'] = {'mttr_medio': average(mttr), 'mtbf_medio': average(mtbf),
                             'disponibilidade_media': average(availability), 'custo_total_manutencao': cost}
    result['detalhes_equipamentos'] = items
    result['desempenho'] = {'mttr': average(mttr, None), 'mtbf': average(mtbf, None),
                            'disponibilidade': average(availability, None), 'custo': cost}
    result['custos_por_dia'] = list(HistoricoManutencao.objects.filter(ordem_servico__in=completed).order_by(
        'data_execucao').values('data_execucao').annotate(pecas=Sum('custo_pecas'), mao_de_obra=Sum('custo_mao_de_obra')))
    return result
