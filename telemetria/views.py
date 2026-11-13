from rest_framework import viewsets, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from .models import Sensor, Telemetria, TrendConfig
from .serializers import SensorSerializer, TelemetriaSerializer, TrendConfigSerializer
from .trend_analysis import analyze_sensor_trend, get_all_sensor_trends
from .work_order_context import attach_predictive_order_summaries
from accounts.permissions import IsAuthenticatedNoDeleteForTecnico


def operational_scope(qs, request, equipment_field):
    """Opt-in scope for the live chart, matching the technician's visible orders."""
    if request.user.tipo_usuario == 'tecnico' and request.query_params.get('escopo_operacional') == 'true':
        from manutencao.models import OrdemServico
        ids = OrdemServico.objects.filter(equipamento__empresa_id=request.user.empresa_id).filter(
            models.Q(responsavel=request.user) | models.Q(responsavel__isnull=True)
        ).values('equipamento_id')
        qs = qs.filter(**{equipment_field + '__in': ids})
    return qs


class SensorViewSet(viewsets.ModelViewSet):
    serializer_class = SensorSerializer
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['equipamento', 'equipamento__empresa', 'tipo', 'ativo']
    search_fields = ['nome', 'descricao', 'equipamento__nome']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Sensor.objects.none()
        user = self.request.user
        qs = Sensor.objects.select_related('equipamento').order_by('nome', 'pk')
        if user.tipo_usuario != 'admin':
            if user.empresa:
                qs = qs.filter(equipamento__empresa=user.empresa)
            else:
                return qs.none()
        qs = operational_scope(qs, self.request, 'equipamento_id')
        equipamento_ids = self.request.query_params.get('equipamento__in')
        if equipamento_ids:
            try:
                ids = [int(value) for value in equipamento_ids.split(',') if value.strip()]
            except ValueError:
                ids = []
            qs = qs.filter(equipamento_id__in=ids)
        return qs


from django_filters import rest_framework as df_filters

class TelemetriaFilter(df_filters.FilterSet):
    id_ate = df_filters.NumberFilter(field_name='id', lookup_expr='lte')
    valor_min = df_filters.NumberFilter(field_name="valor", lookup_expr='gte')
    valor_max = df_filters.NumberFilter(field_name="valor", lookup_expr='lte')
    timestamp_de = df_filters.DateTimeFilter(field_name='timestamp', lookup_expr='gte')
    timestamp_ate = df_filters.DateTimeFilter(field_name='timestamp', lookup_expr='lte')

    class Meta:
        model = Telemetria
        fields = ['sensor', 'sensor__equipamento', 'sensor__equipamento__empresa', 'valor_min', 'valor_max', 'timestamp_de', 'timestamp_ate']

class TelemetriaViewSet(viewsets.ModelViewSet):
    serializer_class = TelemetriaSerializer
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]
    filter_backends = [DjangoFilterBackend]
    filterset_class = TelemetriaFilter

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Telemetria.objects.none()
        user = self.request.user
        qs = Telemetria.objects.select_related('sensor', 'sensor__equipamento').order_by('-timestamp', '-pk')
        if user.tipo_usuario != 'admin':
            if user.empresa:
                qs = qs.filter(sensor__equipamento__empresa=user.empresa)
            else:
                return qs.none()

        qs = operational_scope(qs, self.request, 'sensor__equipamento_id')
        equipamento_ids = self.request.query_params.get('sensor__equipamento__in')
        if equipamento_ids:
            try:
                ids = [int(value) for value in equipamento_ids.split(',') if value.strip()]
            except ValueError:
                ids = []
            qs = qs.filter(sensor__equipamento_id__in=ids)
        return qs


class TrendConfigViewSet(viewsets.ModelViewSet):
    """CRUD para configurações de análise de tendência."""
    serializer_class = TrendConfigSerializer
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {'sensor': ['exact', 'isnull'], 'ativo': ['exact']}

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return TrendConfig.objects.none()
        user = self.request.user
        qs = TrendConfig.objects.select_related('sensor', 'sensor__equipamento').order_by('-pk')
        if user.tipo_usuario != 'admin':
            if user.empresa:
                qs = qs.filter(sensor__equipamento__empresa=user.empresa)
            else:
                return qs.none()
        return qs


class TrendDashboardView(APIView):
    """
    GET /api/telemetria/tendencias/
    Retorna sensores com tendências atípicas (para o painel do dashboard).

    Query params:
        ?sensor_id=1    → Análise de um sensor específico
        ?all=true       → Retorna todos (não apenas atípicos)
    """
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]

    @extend_schema(responses=OpenApiTypes.ANY)
    def get(self, request):
        sensor_id = request.query_params.get('sensor_id')

        if sensor_id:
            try:
                sensor_id = int(sensor_id)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'O parâmetro sensor_id deve ser um número inteiro.'},
                    status=400
                )

            sensor_queryset = Sensor.objects.filter(pk=sensor_id, ativo=True)
            if request.user.tipo_usuario != 'admin':
                if not request.user.empresa:
                    return Response(
                        {'detail': 'Sensor não encontrado ou inativo.'},
                        status=404
                    )
                sensor_queryset = sensor_queryset.filter(
                    equipamento__empresa=request.user.empresa
                )

            if not sensor_queryset.exists():
                return Response(
                    {'detail': 'Sensor não encontrado ou inativo.'},
                    status=404
                )

            trend = analyze_sensor_trend(int(sensor_id))
            if trend is None:
                return Response(
                    {'detail': 'Sensor não encontrado ou inativo.'},
                    status=404
                )
            attach_predictive_order_summaries([trend], request.user)
            return Response(trend)

        show_all = request.query_params.get('all', 'false').lower() == 'true'
        trends = get_all_sensor_trends(
            request.user,
            only_atypical=not show_all,
            empresa_id=request.query_params.get('empresa_id'),
        )
        return Response(attach_predictive_order_summaries(trends, request.user))
