from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer
from django.db.models import Avg, F, ExpressionWrapper, DurationField, Sum
from django.utils import timezone
from manutencao.models import OrdemServico, HistoricoManutencao
from ativos.models import Equipamento
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
        # Nota: apenas intervalos positivos são considerados. Intervalos negativos ou zero
        # indicam dados inconsistentes (ex: data_conclusao carimbada errada) e são ignorados.
        inter_failure_times = []
        last_conclusao = None
        for os in os_eq:
            if os.data_conclusao:
                if last_conclusao:
                    intervalo = os.data_abertura - last_conclusao
                    if intervalo.total_seconds() > 0:  # ignora intervalos negativos/zerados
                        inter_failure_times.append(intervalo)
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
            'amostras_mtbf': len(inter_failure_times),
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

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        from .summary import build_summary
        return Response(build_summary(request, KpiService))


class KpiDashboardView(APIView):
    """
    GET /api/dashboards/kpis/
    KPIs individuais por equipamento.

    Parâmetros opcionais:
        ?equipamento_id=1  → Filtra por equipamento específico
        ?dias=30           → Limita às OS dos últimos N dias
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=inline_serializer(
            name='KpiDashboardItem',
            many=True,
            fields={
                'equipamento': serializers.CharField(),
                'equipamento_id': serializers.IntegerField(),
                'status': serializers.CharField(),
                'mttr_hours': serializers.FloatField(),
                'mtbf_hours': serializers.FloatField(),
                'disponibilidade_porcentagem': serializers.FloatField(allow_null=True),
                'total_manutencoes': serializers.IntegerField(),
                'custo_total_manutencao': serializers.FloatField(),
            },
        )
    )
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