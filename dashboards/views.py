from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, F, ExpressionWrapper, DurationField
from manutencao.models import OrdemServico
from ativos.models import Equipamento
from datetime import timedelta


class KpiService:
    @staticmethod
    def calcular_kpi(equipamento, os_queryset):
        os_eq = os_queryset.filter(equipamento=equipamento).order_by('data_abertura')

        # MTTR — média de duração das manutenções
        mttr_data = os_eq.annotate(
            duration=ExpressionWrapper(
                F('data_conclusao') - F('data_abertura'),
                output_field=DurationField()
            )
        ).aggregate(avg_mttr=Avg('duration'))

        mttr = mttr_data['avg_mttr'] if mttr_data['avg_mttr'] else timedelta(0)

        # MTBF — tempo médio entre falhas
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

        # Disponibilidade
        total_time = mtbf + mttr
        if total_time.total_seconds() > 0:
            disponibilidade = (mtbf.total_seconds() / total_time.total_seconds()) * 100
        else:
            disponibilidade = 100.0 if equipamento.status == 'ativo' else 0.0

        return {
            'equipamento': equipamento.nome,
            'equipamento_id': equipamento.id,
            'mttr_hours': round(mttr.total_seconds() / 3600, 2),
            'mtbf_hours': round(mtbf.total_seconds() / 3600, 2),
            'disponibilidade_porcentagem': round(disponibilidade, 2),
            'total_manutencoes': os_eq.count(),
        }


class KpiDashboardView(APIView):
    """
    GET /api/dashboards/kpi/
    Parâmetro opcional: ?equipamento_id=<id>
    Retorna MTTR, MTBF e Disponibilidade filtrados pela empresa do usuário logado.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        equipamento_id = request.query_params.get('equipamento_id')

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

        results = [
            KpiService.calcular_kpi(eq, os_queryset)
            for eq in equipamentos
        ]

        return Response(results)