from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as df_filters
from .models import OrdemServico, HistoricoManutencao
from .filters import OrdemServicoFilter
from .ordering import ordenar_ordens
from .services import alterar_prioridade
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.permissions import IsGestor
from .serializers import AjustePrioridadeSerializer, RestaurarPrioridadeSerializer, HistoricoPrioridadeOSSerializer
from .serializers import OrdemServicoSerializer, HistoricoManutencaoSerializer
from .permissions import IsOwnerOrGestorOrUnassigned
from accounts.permissions import IsAuthenticatedNoDeleteForTecnico
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse
from gemini_api.serializers import GeminiResponseSerializer
import logging


logger = logging.getLogger(__name__)


class HistoricoManutencaoFilter(df_filters.FilterSet):
    # ... (rest of filter class)
    data_execucao_depois = df_filters.DateFilter(field_name='data_execucao', lookup_expr='gte')
    data_execucao_antes = df_filters.DateFilter(field_name='data_execucao', lookup_expr='lte')

    class Meta:
        model = HistoricoManutencao
        fields = [
            'ordem_servico', 'ordem_servico__equipamento__empresa',
            'data_execucao_depois', 'data_execucao_antes'
        ]




class OrdemServicoViewSet(viewsets.ModelViewSet):
    serializer_class = OrdemServicoSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrGestorOrUnassigned]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = OrdemServicoFilter
    search_fields = ['titulo', 'descricao']

    @extend_schema(request=None, responses={
        200: GeminiResponseSerializer,
        502: OpenApiResponse(description='Falha no provedor ou resposta vazia.'),
        503: OpenApiResponse(description='IA indisponível ou não configurada.'),
    })
    @action(detail=True, methods=['post'], url_path='analise-ia')
    def analise_ia(self, request, pk=None):
        from gemini_api.cliente import generate_content, is_gemini_available
        from gemini_api.order_analysis import build_order_analysis_prompts

        # Authorize the selected OS before building context or calling the provider.
        order = self.get_object()
        if not is_gemini_available():
            return Response(
                {'detail': 'A análise por IA está indisponível. Contate o administrador.'}, status=503,
            )
        system, context = build_order_analysis_prompts(order, self.get_queryset())
        try:
            text, model = generate_content(
                system_instruction=system, user_prompt=context, temperature=0.35,
            )
            if not isinstance(text, str) or not text.strip():
                raise ValueError('Gemini retornou uma análise vazia.')
        except Exception:
            logger.exception('Falha na análise por IA da OS %s', order.pk)
            return Response(
                {'detail': 'Não foi possível gerar a análise. Tente novamente.'}, status=502,
            )
        response = Response({'response': text.strip(), 'model_used': model})
        response['Cache-Control'] = 'no-store'
        return response

    def list(self, request, *args, **kwargs):
        visible = self.get_queryset()
        qs = self.filter_queryset(visible)
        page = self.paginate_queryset(qs)
        response = self.get_paginated_response(self.get_serializer(page, many=True).data)
        response.data['a_definir'] = qs.filter(prioridade__isnull=True).count()
        response.data['total_escopo'] = visible.count()
        return response

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGestor], serializer_class=AjustePrioridadeSerializer)
    def ajustar_prioridade(self, request, pk=None):
        obj = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = alterar_prioridade(obj, request.user, **serializer.validated_data)
        return Response(OrdemServicoSerializer(obj).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsGestor], serializer_class=RestaurarPrioridadeSerializer)
    def restaurar_prioridade(self, request, pk=None):
        obj = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = alterar_prioridade(obj, request.user, restaurar=True, **serializer.validated_data)
        return Response(OrdemServicoSerializer(obj).data)

    @action(detail=True, methods=['get'], serializer_class=HistoricoPrioridadeOSSerializer)
    def historico_prioridade(self, request, pk=None):
        qs = self.get_object().historico_prioridade.select_related('alterado_por')
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


    @transaction.atomic
    def perform_create(self, serializer):
        validated = serializer.validated_data
        status = validated.get('status')
        responsavel = validated.get('responsavel')
        if status == 'concluida' and responsavel is None:
            serializer.save(responsavel=self.request.user)
        else:
            serializer.save()

    @transaction.atomic
    def perform_update(self, serializer):
        serializer.instance = self.get_queryset().select_for_update(of=('self',)).get(pk=serializer.instance.pk)
        self.check_object_permissions(self.request, serializer.instance)
        serializer.validate(dict(serializer.validated_data))
        validated = serializer.validated_data
        status = validated.get('status', serializer.instance.status)
        responsavel = validated.get('responsavel', serializer.instance.responsavel)
        if status == 'concluida' and responsavel is None:
            serializer.save(responsavel=self.request.user)
        else:
            serializer.save()

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return OrdemServico.objects.none()
        user = self.request.user
        qs = ordenar_ordens(OrdemServico.objects.select_related('equipamento', 'responsavel', 'criterios_criticidade_na_abertura__criado_por'))
        
        if user.tipo_usuario == 'admin':
            return qs.all()
        
        if user.empresa:
            base_qs = qs.filter(equipamento__empresa=user.empresa)
            
            # Lógica de Visibilidade para Técnicos
            if user.tipo_usuario == 'tecnico':
                from django.db.models import Q
                # Técnico vê: O.S. sem dono OU O.S. que pertence a ele
                return base_qs.filter(Q(responsavel=user) | Q(responsavel__isnull=True))
            
            return base_qs
            
        return qs.none()


class HistoricoManutencaoViewSet(viewsets.ModelViewSet):
    serializer_class = HistoricoManutencaoSerializer
    permission_classes = [IsAuthenticatedNoDeleteForTecnico]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = HistoricoManutencaoFilter
    search_fields = ['descricao_servico']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return HistoricoManutencao.objects.none()
        user = self.request.user
        qs = HistoricoManutencao.objects.select_related('ordem_servico')
        if user.tipo_usuario == 'admin':
            return qs.all()
        if user.empresa:
            return qs.filter(ordem_servico__equipamento__empresa=user.empresa)
        return qs.none()
