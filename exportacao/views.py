"""
Views de exportação de dados do NanaSmart.

Cada view retorna os dados no formato solicitado (csv, excel, pdf),
aplicando o mesmo isolamento multi-tenant das views originais.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from .utils import ExportadorFactory

from manutencao.views import OrdemServicoViewSet
from manutencao.models import OrdemServico, HistoricoManutencao
from ativos.models import Equipamento
from alertas.models import Alerta
from telemetria.models import Sensor, Telemetria


# ═════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════

def _filtrar_por_empresa(queryset, user, campo_empresa='empresa'):
    """Aplica o isolamento multi-tenant padrão do NanaSmart."""
    if user.tipo_usuario == 'admin':
        empresa_id = None  # admin vê tudo por padrão
        return queryset
    if user.empresa:
        return queryset.filter(**{campo_empresa: user.empresa})
    return queryset.none()


def _filtrar_empresa_admin(queryset, user, empresa_id, campo_empresa):
    if user.tipo_usuario == 'admin':
        if empresa_id:
            return queryset.filter(**{f'{campo_empresa}_id': empresa_id})
        return queryset
    if user.empresa:
        return queryset.filter(**{campo_empresa: user.empresa})
    return queryset.none()


def _despachar_formato(formato, nome, titulo, colunas, linhas):
    """Despacha para o exporter correto baseado no formato solicitado."""
    try:
        exportador = ExportadorFactory.criar(formato)
        return exportador.exportar(nome, titulo, colunas, linhas)
    except ValueError:
        return Response(
            {'error': f'Formato "{formato}" inválido. Use: csv, excel ou pdf.'},
            status=400
        )


def _formatar_datetime(dt):
    """Formata datetime para string legível ou retorna '—'."""
    if dt:
        return timezone.localtime(dt).strftime('%d/%m/%Y %H:%M')
    return '—'


def _formatar_date(d):
    """Formata date para string legível ou retorna '—'."""
    if d:
        return d.strftime('%d/%m/%Y')
    return '—'


# ═════════════════════════════════════════════════════════════════════
# Views de Exportação
# ═════════════════════════════════════════════════════════════════════

class ExportarOrdensServicoView(APIView):
    """
    GET /api/exportar/ordens-servico/{formato}/

    Exporta Ordens de Serviço em CSV, Excel ou PDF.

    Query params opcionais:
        ?status=pendente
        ?prioridade=A
        ?tipo_os=corretiva
        ?equipamento=1
        ?responsavel=2
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.BINARY, 400: OpenApiTypes.OBJECT})
    def get(self, request, formato):
        view = OrdemServicoViewSet()
        view.request, view.args, view.kwargs, view.action = request, (), {}, 'list'
        qs = view.filter_queryset(view.get_queryset())

        colunas = [
            'ID', 'Título', 'Equipamento', 'Tipo OS', 'Status',
            'Prioridade', 'Criticidade atual', 'Origem da prioridade', 'Responsável', 'Data Abertura', 'Data Conclusão'
        ]

        linhas = []
        for os in qs:
            linhas.append([
                os.id,
                os.titulo,
                os.equipamento.nome if os.equipamento else '—',
                os.get_tipo_os_display(),
                os.get_status_display(),
                os.get_prioridade_display() or 'A definir',
                os.equipamento.get_criticidade_display() or 'Não avaliada',
                os.get_prioridade_origem_display(),
                os.responsavel.get_full_name() or os.responsavel.username if os.responsavel else 'Sem responsável',
                _formatar_datetime(os.data_abertura),
                _formatar_datetime(os.data_conclusao),
            ])

        return _despachar_formato(formato, 'ordens_servico', 'Ordens de Serviço', colunas, linhas)


class ExportarEquipamentosView(APIView):
    """
    GET /api/exportar/equipamentos/{formato}/

    Exporta Equipamentos em CSV, Excel ou PDF.

    Query params opcionais:
        ?status=ativo
        ?tipo=motor_eletrico
        ?empresa=1
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.BINARY, 400: OpenApiTypes.OBJECT})
    def get(self, request, formato):
        user = request.user
        qs = Equipamento.objects.select_related('empresa')

        # Isolamento multi-tenant
        qs = _filtrar_empresa_admin(qs, user, request.query_params.get('empresa'), 'empresa')

        # Filtros opcionais
        status = request.query_params.get('status')
        tipo = request.query_params.get('tipo')

        if status:
            qs = qs.filter(status=status)
        if tipo:
            qs = qs.filter(tipo=tipo)

        if request.query_params.get('criticidade'):
            qs = qs.filter(criticidade=request.query_params['criticidade'])
        if request.query_params.get('search'):
            from django.db.models import Q
            term = request.query_params['search']
            qs = qs.filter(Q(nome__icontains=term) | Q(numero_serie__icontains=term) | Q(fabricante__icontains=term) | Q(modelo__icontains=term))
        qs = qs.order_by('nome')

        colunas = [
            'ID', 'Nome', 'Tipo', 'Fabricante', 'Modelo',
            'Nº Série', 'Status', 'Criticidade', 'Horímetro (h)', 'Empresa'
        ]

        linhas = []
        for eq in qs:
            linhas.append([
                eq.id,
                eq.nome,
                eq.tipo or '—',
                eq.fabricante or '—',
                eq.modelo or '—',
                eq.numero_serie,
                eq.get_status_display(),
                eq.get_criticidade_display() or 'Não avaliada',
                round(eq.horimetro, 1),
                eq.empresa.nome if eq.empresa else '—',
            ])

        return _despachar_formato(formato, 'equipamentos', 'Equipamentos', colunas, linhas)


class ExportarAlertasView(APIView):
    """Exporta o mesmo histórico e os mesmos filtros de /api/alertas/."""
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.BINARY, 400: OpenApiTypes.OBJECT})
    def get(self, request, formato):
        from alertas.filters import AlertaFilter, ordenar_historico
        from alertas.serializers import AlertaSerializer
        qs = _filtrar_por_empresa(
            Alerta.objects.select_related('equipamento', 'sensor', 'ordem_servico_preditiva'),
            request.user, 'equipamento__empresa',
        )
        selection = AlertaFilter(request.query_params, queryset=qs)
        if not selection.is_valid():
            return Response(selection.errors, status=400)
        qs = ordenar_historico(selection.qs)
        colunas = ['ID', 'Equipamento', 'Sensor', 'Origem', 'Tipo Alerta', 'Nível inicial',
                   'Nível máximo', 'Motivo da detecção', 'Data Alerta', 'Normalização detectada', 'O.S.', 'Legado']
        linhas = []
        for alerta in qs:
            evidence = alerta.dados_deteccao or {}
            legado = not evidence or evidence.get('legado', False)
            linhas.append([
                alerta.pk, evidence.get('equipamento_nome', alerta.equipamento.nome),
                evidence.get('sensor_nome', alerta.sensor.nome if alerta.sensor_id else '—'),
                alerta.get_origem_display(), evidence.get('tipo_alerta', alerta.tipo_alerta),
                evidence.get('nivel', 'Não disponível'), alerta.get_nivel_display(),
                evidence.get('descricao', alerta.descricao), _formatar_datetime(alerta.data_alerta),
                _formatar_datetime(alerta.data_normalizacao),
                AlertaSerializer().get_ordem_servico_id(alerta) or '—', 'Sim' if legado else 'Não',
            ])
        return _despachar_formato(formato, 'alertas', 'Histórico de alertas', colunas, linhas)


class ExportarTelemetriaView(APIView):
    """
    GET /api/exportar/telemetria/{formato}/

    Exporta leituras de Telemetria em CSV, Excel ou PDF.

    Query params opcionais:
        ?sensor=1
        ?sensor__equipamento=2
        ?limite=1000  (máximo de registros, padrão: 5000)
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.BINARY, 400: OpenApiTypes.OBJECT})
    def get(self, request, formato):
        user = request.user
        qs = Telemetria.objects.select_related('sensor', 'sensor__equipamento')

        # Isolamento multi-tenant
        if user.tipo_usuario == 'admin':
            pass
        elif user.empresa:
            qs = qs.filter(sensor__equipamento__empresa=user.empresa)
        else:
            return Response({'error': 'Usuário sem empresa vinculada.'}, status=400)

        # Filtros opcionais
        sensor_id = request.query_params.get('sensor')
        equipamento_id = request.query_params.get('sensor__equipamento')

        if sensor_id:
            qs = qs.filter(sensor_id=sensor_id)
        if equipamento_id:
            qs = qs.filter(sensor__equipamento_id=equipamento_id)
        if user.tipo_usuario == 'admin' and request.query_params.get('empresa'):
            qs = qs.filter(sensor__equipamento__empresa_id=request.query_params['empresa'])

        # Limitar quantidade para não travar (padrão: 5000)
        try:
            limite = int(request.query_params.get('limite', 5000))
        except ValueError:
            limite = 5000
        limite = min(limite, 10000)  # máximo absoluto

        qs = qs.order_by('-timestamp')[:limite]

        colunas = [
            'ID', 'Sensor', 'Equipamento', 'Tipo Sensor',
            'Valor', 'Unidade', 'Timestamp'
        ]

        linhas = []
        for leitura in qs:
            linhas.append([
                leitura.id,
                leitura.sensor.nome,
                leitura.sensor.equipamento.nome,
                leitura.sensor.get_tipo_display(),
                round(leitura.valor, 2),
                leitura.sensor.unidade_medida,
                _formatar_datetime(leitura.timestamp),
            ])

        return _despachar_formato(formato, 'telemetria', 'Telemetria — Leituras de Sensores', colunas, linhas)


class ExportarHistoricoView(APIView):
    """
    GET /api/exportar/historico/{formato}/

    Exporta Histórico de Manutenção em CSV, Excel ou PDF.

    Query params opcionais:
        ?ordem_servico=1
        ?data_execucao_depois=2025-01-01
        ?data_execucao_antes=2025-12-31
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.BINARY, 400: OpenApiTypes.OBJECT})
    def get(self, request, formato):
        user = request.user
        qs = HistoricoManutencao.objects.select_related(
            'ordem_servico', 'ordem_servico__equipamento'
        )

        # Isolamento multi-tenant
        if user.tipo_usuario == 'admin':
            pass
        elif user.empresa:
            qs = qs.filter(ordem_servico__equipamento__empresa=user.empresa)
        else:
            return Response({'error': 'Usuário sem empresa vinculada.'}, status=400)

        # Filtros opcionais
        os_id = request.query_params.get('ordem_servico')
        data_depois = request.query_params.get('data_execucao_depois')
        data_antes = request.query_params.get('data_execucao_antes')

        if os_id:
            qs = qs.filter(ordem_servico_id=os_id)
        if data_depois:
            qs = qs.filter(data_execucao__gte=data_depois)
        if data_antes:
            qs = qs.filter(data_execucao__lte=data_antes)
        if user.tipo_usuario == 'admin' and request.query_params.get('empresa'):
            qs = qs.filter(ordem_servico__equipamento__empresa_id=request.query_params['empresa'])

        qs = qs.order_by('-data_execucao')

        colunas = [
            'ID', 'OS Vinculada', 'Equipamento', 'Descrição Serviço',
            'Data Execução', 'Custo Peças (R$)', 'Custo Mão de Obra (R$)', 'Custo Total (R$)'
        ]

        linhas = []
        for h in qs:
            linhas.append([
                h.id,
                f'OS #{h.ordem_servico.id} — {h.ordem_servico.titulo}',
                h.ordem_servico.equipamento.nome if h.ordem_servico.equipamento else '—',
                h.descricao_servico[:80] + ('...' if len(h.descricao_servico) > 80 else ''),
                _formatar_date(h.data_execucao),
                f'{h.custo_pecas:.2f}',
                f'{h.custo_mao_de_obra:.2f}',
                f'{h.custo_total:.2f}',
            ])

        return _despachar_formato(formato, 'historico_manutencao', 'Histórico de Manutenção', colunas, linhas)


class ExportarDashboardView(APIView):
    """
    GET /api/exportar/dashboard/{formato}/

    Exporta KPIs do Dashboard em CSV, Excel ou PDF.

    Query params opcionais:
        ?empresa_id=1  (apenas admin)
        ?dias=30
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.BINARY, 400: OpenApiTypes.OBJECT})
    def get(self, request, formato):
        from manutencao.dashboards.views import KpiService
        from datetime import timedelta

        user = request.user
        dias = request.query_params.get('dias')
        empresa_id = request.query_params.get('empresa_id')

        # Filtro base por empresa
        eq_filter = {}
        if user.tipo_usuario == 'admin':
            if empresa_id:
                eq_filter['empresa_id'] = empresa_id
        elif user.empresa:
            eq_filter['empresa'] = user.empresa
        else:
            return Response({'error': 'Usuário sem empresa vinculada.'}, status=400)

        equipamentos = Equipamento.objects.filter(**eq_filter)
        if request.query_params.get('setor'):
            equipamentos = equipamentos.filter(localizacao__setor=request.query_params['setor'])
        if request.query_params.get('equipamento_id'):
            equipamentos = equipamentos.filter(pk=request.query_params['equipamento_id'])


        # Base de OS concluídas
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
                pass

        # Calcula KPIs por equipamento
        kpis = [KpiService.calcular_kpi(eq, os_base) for eq in equipamentos]

        colunas = [
            'Equipamento', 'Status', 'MTTR (horas)', 'MTBF (horas)',
            'Disponibilidade (%)', 'Total Manutenções', 'Custo Total (R$)'
        ]

        linhas = []
        for k in kpis:
            linhas.append([
                k['equipamento'],
                k['status'],
                k['mttr_hours'],
                k['mtbf_hours'],
                k['disponibilidade_porcentagem'] if k['disponibilidade_porcentagem'] is not None else '—',
                k['total_manutencoes'],
                f"{k['custo_total_manutencao']:.2f}",
            ])

        return _despachar_formato(formato, 'dashboard_kpis', 'Dashboard — KPIs por Equipamento', colunas, linhas)
