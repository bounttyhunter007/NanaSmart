from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, F, ExpressionWrapper, DurationField, Count, Sum
from django.utils import timezone
from manutencao.models import OrdemServico, HistoricoManutencao
from ativos.models import Equipamento
from alertas.models import Alerta
from datetime import timedelta


class KpiService:
    @staticmethod
    def calcular_kpi(equipamento, os_queryset):
        os_eq = os_queryset.filter(equipamento=equipamento).order_by('data_abertura')

        # MTTR — média de duração das manutenções concluídas
        mttr_data = os_eq.annotate(
            duration=ExpressionWrapper(
                F('data_conclusao') - F('data_abertura'),
                output_field=DurationField()
            )
        ).aggregate(avg_mttr=Avg('duration'))

        mttr = mttr_data['avg_mttr'] if mttr_data['avg_mttr'] else timedelta(0)

        # MTBF — tempo médio entre falhas (intervalo entre fim de uma OS e início da próxima)
        inter_failure_times = []
        last_conclusao = None
        for os in os_eq:
            if os.data_conclusao:
                if last_conclusao:
                    inter_failure_times.append(os.data_abertura - last_conclusao)
                last_conclusao = os.data_conclusao

        if inter_failure_times:
            mtbf = sum(inter_failure_times, timedelta(0)) / len(inter_failure_times)
        else:
            mtbf = timedelta(0)

        # Disponibilidade — calculada só se houver histórico real
        total_manutencoes = os_eq.count()
        if total_manutencoes > 0:
            total_time = mtbf + mttr
            if total_time.total_seconds() > 0:
                disponibilidade = (mtbf.total_seconds() / total_time.total_seconds()) * 100
            else:
                disponibilidade = 100.0
        else:
            # Sem histórico: não distorce a média — retorna None para ser ignorado nas médias globais
            disponibilidade = None

        # Custo total das manutenções deste equipamento
        custo = HistoricoManutencao.objects.filter(
            ordem_servico__in=os_eq
        ).aggregate(
            total_pecas=Sum('custo_pecas'),
            total_mao=Sum('custo_mao_de_obra')
        )
        custo_total = float((custo['total_pecas'] or 0) + (custo['total_mao'] or 0))

        return {
            'equipamento': equipamento.nome,
            'equipamento_id': equipamento.id,
            'status': equipamento.status,
            'mttr_hours': round(mttr.total_seconds() / 3600, 2),
            'mtbf_hours': round(mtbf.total_seconds() / 3600, 2),
            'disponibilidade_porcentagem': round(disponibilidade, 2) if disponibilidade is not None else None,
            'total_manutencoes': total_manutencoes,
            'custo_total_manutencao': round(custo_total, 2),
        }


class DashboardSummaryView(APIView):
    """
    GET /api/dashboards/resumo/

    Parâmetros opcionais:
        ?empresa_id=1      → Admin filtra por empresa específica
        ?dias=30           → Limita KPIs às OS dos últimos N dias (padrão: todo o histórico)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        empresa_id = request.query_params.get('empresa_id')
        dias = request.query_params.get('dias')

        # Filtro base por empresa (isolamento multi-tenant)
        eq_filter = {}
        if user.tipo_usuario == 'admin':
            if empresa_id:
                eq_filter['empresa_id'] = empresa_id
        elif user.empresa:
            eq_filter['empresa'] = user.empresa
        else:
            return Response({'error': 'Usuário sem empresa vinculada.'}, status=400)

        equipamentos = Equipamento.objects.filter(**eq_filter)

        # 1. Contagens de Status dos equipamentos
        status_counts = equipamentos.values('status').annotate(total=Count('status'))
        resumo_status = {'total': equipamentos.count(), 'ativo': 0, 'manutencao': 0, 'inativo': 0}
        for item in status_counts:
            resumo_status[item['status']] = item['total']

        # 2. Base de OS — filtra por período se solicitado
        os_base = OrdemServico.objects.filter(
            status='concluida',
            data_conclusao__isnull=False,
            equipamento__in=equipamentos
        )
        if dias:
            try:
                desde = timezone.now() - timedelta(days=int(dias))
                os_base = os_base.filter(data_abertura__gte=desde)
            except ValueError:
                pass  # Ignora valor inválido de dias

        # 3. KPIs por equipamento
        individual_kpis = [KpiService.calcular_kpi(eq, os_base) for eq in equipamentos]

        # Médias globais — exclui equipamentos sem histórico da média de disponibilidade
        valid_mttr = [k['mttr_hours'] for k in individual_kpis if k['total_manutencoes'] > 0]
        valid_mtbf = [k['mtbf_hours'] for k in individual_kpis if k['mtbf_hours'] > 0]
        valid_disp = [k['disponibilidade_porcentagem'] for k in individual_kpis if k['disponibilidade_porcentagem'] is not None]

        avg_mttr = round(sum(valid_mttr) / len(valid_mttr), 2) if valid_mttr else 0
        avg_mtbf = round(sum(valid_mtbf) / len(valid_mtbf), 2) if valid_mtbf else 0
        avg_disp = round(sum(valid_disp) / len(valid_disp), 2) if valid_disp else 0
        custo_total_geral = round(sum(k['custo_total_manutencao'] for k in individual_kpis), 2)

        # 4. Alertas ativos da empresa
        alertas_ativos = Alerta.objects.filter(
            equipamento__in=equipamentos,
            status='ativo'
        ).values('nivel').annotate(total=Count('nivel'))
        resumo_alertas = {'critico': 0, 'medio': 0, 'baixo': 0, 'total': 0}
        for a in alertas_ativos:
            resumo_alertas[a['nivel']] = a['total']
            resumo_alertas['total'] += a['total']

        # 5. OS abertas (pendente + andamento)
        os_abertas = OrdemServico.objects.filter(
            equipamento__in=equipamentos,
            status__in=['pendente', 'andamento']
        ).count()

        return Response({
            'resumo_status': resumo_status,
            'kpis_globais': {
                'mttr_medio': avg_mttr,
                'mtbf_medio': avg_mtbf,
                'disponibilidade_media': avg_disp,
                'custo_total_manutencao': custo_total_geral,
            },
            'alertas_ativos': resumo_alertas,
            'os_abertas': os_abertas,
            'detalhes_equipamentos': individual_kpis,
        })


class KpiDashboardView(APIView):
    """
    GET /api/dashboards/kpis/
    KPIs individuais por equipamento.

    Parâmetros opcionais:
        ?equipamento_id=1  → Filtra por equipamento específico
        ?dias=30           → Limita às OS dos últimos N dias
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        equipamento_id = request.query_params.get('equipamento_id')
        dias = request.query_params.get('dias')

        os_queryset = OrdemServico.objects.filter(
            status='concluida',
            data_conclusao__isnull=False,
        ).select_related('equipamento')

        if user.tipo_usuario == 'admin':
            equipamentos = Equipamento.objects.all()
        elif user.empresa:
            equipamentos = Equipamento.objects.filter(empresa=user.empresa)
            os_queryset = os_queryset.filter(equipamento__empresa=user.empresa)
        else:
            return Response([])

        if equipamento_id:
            equipamentos = equipamentos.filter(pk=equipamento_id)

        if dias:
            try:
                desde = timezone.now() - timedelta(days=int(dias))
                os_queryset = os_queryset.filter(data_abertura__gte=desde)
            except ValueError:
                pass

        results = [KpiService.calcular_kpi(eq, os_queryset) for eq in equipamentos]
        return Response(results)