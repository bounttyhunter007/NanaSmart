from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status as http_status
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .cliente import generate_content, is_gemini_available
from .facades import GeminiContextFacade
from .models import PromptAnaliseOS, PromptConfig
from .order_analysis import prompt_config_data
from accounts.models import Empresa
from .prompt_builder import (
    build_system_instruction,
    build_chat_prompt,
    build_os_analysis_prompt,
    build_unassigned_orders_prompt,
    build_finance_prompt,
    build_trend_analysis_prompt,
    get_all_defaults,
)
from telemetria.trend_analysis import analyze_sensor_trend
from telemetria.models import Sensor
from .serializers import (
    GeminiMessageSerializer,
    GeminiResponseSerializer,
    PromptConfigSerializer,
    PromptAnaliseOSSerializer,
)


class CanConfigureOsAnalysis(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo_usuario in ('admin', 'gestor')


@extend_schema(parameters=[OpenApiParameter(
    'empresa', int, description='Obrigatória para administrador. Gestores só podem informar a própria empresa.',
)])
class PromptAnaliseOSView(APIView):
    permission_classes = [IsAuthenticated, CanConfigureOsAnalysis]
    serializer_class = PromptAnaliseOSSerializer

    def get_company_id(self, request):
        selected = request.query_params.get('empresa')
        if request.user.tipo_usuario == 'gestor':
            company_id = request.user.empresa_id
            if not company_id:
                raise PermissionDenied('Seu usuário não possui empresa vinculada.')
            if selected is not None and selected != str(company_id):
                raise PermissionDenied('Você só pode configurar a própria empresa.')
            return company_id
        try:
            company_id = int(selected)
        except (TypeError, ValueError):
            raise ValidationError({'empresa': 'Selecione uma empresa.'})
        return get_object_or_404(Empresa, pk=company_id).pk

    @extend_schema(responses=PromptAnaliseOSSerializer)
    def get(self, request):
        return Response(prompt_config_data(self.get_company_id(request)))

    @extend_schema(request=PromptAnaliseOSSerializer, responses=PromptAnaliseOSSerializer)
    def patch(self, request):
        company_id = self.get_company_id(request)
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        PromptAnaliseOS.objects.update_or_create(
            empresa_id=company_id, defaults=serializer.validated_data,
        )
        return Response(prompt_config_data(company_id))


class PromptAnaliseOSResetView(PromptAnaliseOSView):
    http_method_names = ['post', 'options']

    @extend_schema(request=None, responses=PromptAnaliseOSSerializer)
    def post(self, request):
        company_id = self.get_company_id(request)
        # Removing the override restores the current code default, even after updates.
        PromptAnaliseOS.objects.filter(empresa_id=company_id).delete()
        return Response(prompt_config_data(company_id))


class IsAdminUser:
    """Simple permission check: only admin users can access."""
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'tipo_usuario', None) == 'admin'
        )


class PromptConfigListView(APIView):
    """
    GET  — List all prompt configs (auto-seeds defaults if empty).
    """
    permission_classes = [IsAuthenticated, IsAdminUser]

    @extend_schema(
        operation_id='gemini_prompts_list',
        responses=PromptConfigSerializer(many=True),
    )
    def get(self, request):
        # Auto-seed: if no configs exist, create all defaults
        defaults = get_all_defaults()
        if not PromptConfig.objects.exists():
            for key, original in defaults.items():
                label = dict(PromptConfig.PROMPT_KEYS).get(key, key)
                PromptConfig.objects.create(
                    key=key,
                    label=label,
                    original_text=original,
                    custom_text='',
                )

        # Ensure all keys exist (in case new ones were added)
        existing_keys = set(PromptConfig.objects.values_list('key', flat=True))
        for key, original in defaults.items():
            if key not in existing_keys:
                label = dict(PromptConfig.PROMPT_KEYS).get(key, key)
                PromptConfig.objects.create(
                    key=key,
                    label=label,
                    original_text=original,
                    custom_text='',
                )

        configs = PromptConfig.objects.all()
        serializer = PromptConfigSerializer(configs, many=True)
        return Response(serializer.data)


class PromptConfigDetailView(APIView):
    """
    GET    — Retrieve a single prompt config by ID.
    PATCH  — Update custom_text (and optionally label).
    POST   — Reset custom_text to empty (restores original).
    """
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = PromptConfigSerializer

    def get_object(self, pk):
        try:
            return PromptConfig.objects.get(pk=pk)
        except PromptConfig.DoesNotExist:
            return None

    @extend_schema(
        operation_id='gemini_prompt_detail',
        responses=PromptConfigSerializer,
    )
    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'detail': 'Não encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)
        serializer = PromptConfigSerializer(obj)
        return Response(serializer.data)

    @extend_schema(
        request=PromptConfigSerializer,
        responses=PromptConfigSerializer,
    )
    def patch(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return Response({'detail': 'Não encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)
        serializer = PromptConfigSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(responses=PromptConfigSerializer)
    def post(self, request, pk):
        """Reset: clears custom_text so the original is used."""
        obj = self.get_object(pk)
        if not obj:
            return Response({'detail': 'Não encontrado.'}, status=http_status.HTTP_404_NOT_FOUND)
        obj.custom_text = ''
        obj.save()
        serializer = PromptConfigSerializer(obj)
        return Response(serializer.data)


class PromptConfigResetView(PromptConfigDetailView):
    http_method_names = ['post', 'options']

    @extend_schema(
        operation_id='gemini_prompt_reset',
        responses=PromptConfigSerializer,
    )
    def post(self, request, pk):
        return super().post(request, pk)


class GeminiBaseView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GeminiMessageSerializer
    response_serializer_class = GeminiResponseSerializer
    system_purpose = "fornecer orientação de manutenção"
    prompt_builder = None
    temperature = 0.35
    missing_api_suffix = "Adicione a variável GEMINI_API_KEY ao `.env` para habilitar este endpoint."
    forbidden_message = None
    requires_financial_summary = False
    context_facade_class = GeminiContextFacade

    def get_missing_api_response(self):
        return {
            "response": f"A IA do Gemini não está configurada no backend. {self.missing_api_suffix}"
        }

    def check_access(self, user):
        return True

    def get_prompt(self, user, context, message):
        if self.prompt_builder is None:
            return message
        prompt_fn = type(self).prompt_builder
        return prompt_fn(user, context, message)

    def run_gemini(self, system_instruction, user_prompt, history):
        return generate_content(
            system_instruction=system_instruction,
            user_prompt=user_prompt,
            history=history,
            temperature=self.temperature,
        )

    def build_context(self, user):
        return self.context_facade_class().build_context(
            user,
            include_financial_summary=self.requires_financial_summary,
        )

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        message = serializer.validated_data['message']
        history = serializer.validated_data.get('history', [])

        if self.forbidden_message and not self.check_access(user):
            return Response({"response": self.forbidden_message}, status=403)

        if not is_gemini_available():
            return Response(self.get_missing_api_response())

        context = self.build_context(user)

        system_instruction = build_system_instruction(user, self.system_purpose)
        user_prompt = self.get_prompt(user, context, message)

        try:
            response_text, model_used = self.run_gemini(system_instruction, user_prompt, history)
            return Response({"response": response_text, "model_used": model_used})
        except Exception as e:
            return Response({"response": f"Erro ao gerar resposta da IA: {e}"})


class GeminiChatView(GeminiBaseView):
    system_purpose = "responder perguntas gerais sobre o parque de ativos e manutenção"
    prompt_builder = build_chat_prompt
    temperature = 0.4
    missing_api_suffix = "Adicione a variável GEMINI_API_KEY ao `.env` para habilitar o chat."

    @extend_schema(
        request=GeminiMessageSerializer,
        responses=GeminiResponseSerializer,
        description="Pergunte ao assistente de manutenção sobre o parque de ativos e ordens de serviço.",
    )
    def post(self, request):
        return super().post(request)


class GeminiOsAnalysisView(GeminiBaseView):
    system_purpose = "analisar ordens de serviço e indicar ações práticas"
    prompt_builder = build_os_analysis_prompt

    @extend_schema(
        request=GeminiMessageSerializer,
        responses=GeminiResponseSerializer,
        description="Solicite análise das ordens de serviço abertas e recomendações práticas de ação.",
    )
    def post(self, request):
        return super().post(request)


class GeminiUnassignedOrdersView(GeminiBaseView):
    system_purpose = "avaliar ordens sem atribuição e sugerir prioridades"

    def get_prompt(self, user, context, message):
        return build_unassigned_orders_prompt(user, context, message)

    @extend_schema(
        request=GeminiMessageSerializer,
        responses=GeminiResponseSerializer,
        description="Avalie ordens sem atribuição e indique critérios de priorização e alocação.",
    )
    def post(self, request):
        return super().post(request)


class GeminiFinanceView(GeminiBaseView):
    system_purpose = "avaliar custos e gestão financeira de manutenção"
    requires_financial_summary = True
    forbidden_message = (
        "Este endpoint é dedicado a gestores e administradores. "
        "Técnicos podem usar o chat geral ou a análise de ordens de serviço."
    )

    def check_access(self, user):
        return user.tipo_usuario != 'tecnico'

    def get_prompt(self, user, context, message):
        return build_finance_prompt(user, context, message)

    @extend_schema(
        request=GeminiMessageSerializer,
        responses=GeminiResponseSerializer,
        description="Solicite orientação financeira e de redução de custos para manutenção.",
    )
    def post(self, request):
        return super().post(request)


class GeminiTrendAnalysisView(GeminiBaseView):
    system_purpose = "diagnosticar tendências de falha em sensores e sugerir ações preditivas"
    missing_api_suffix = "Adicione a variável GEMINI_API_KEY ao `.env` para habilitar a análise de tendências."

    def get_prompt(self, user, context, message):
        sensor_id = self.request.data.get('sensor_id')
        if not sensor_id:
            raise ValueError("O parâmetro 'sensor_id' é obrigatório no corpo da requisição para análise de tendência.")
        
        trend_data = analyze_sensor_trend(sensor_id)
        if not trend_data:
            raise ValueError("Sensor não encontrado ou não possui dados de tendência.")
            
        return build_trend_analysis_prompt(user, context, message, trend_data)

    @extend_schema(
        request=GeminiMessageSerializer,
        responses=GeminiResponseSerializer,
        description="Analise a tendência de um sensor específico para obter diagnóstico e recomendações preditivas.",
    )
    def post(self, request):
        try:
            sensor_id = int(request.data.get('sensor_id'))
        except (TypeError, ValueError):
            return Response(
                {'sensor_id': 'Informe um ID de sensor inteiro.'},
                status=http_status.HTTP_400_BAD_REQUEST
            )

        sensors = Sensor.objects.filter(pk=sensor_id, ativo=True)
        if request.user.tipo_usuario != 'admin':
            if not request.user.empresa:
                sensors = sensors.none()
            else:
                sensors = sensors.filter(equipamento__empresa=request.user.empresa)

        if not sensors.exists():
            return Response(
                {'detail': 'Sensor não encontrado ou inativo.'},
                status=http_status.HTTP_404_NOT_FOUND
            )

        response = super().post(request)
        # A explicação é enriquecimento opcional: nunca altera a decisão
        # matemática nem impede o alerta/OS se a IA estiver indisponível.
        if response.status_code < 300 and isinstance(getattr(response, 'data', None), dict):
            text = response.data.get('response', '')
            if text and not text.startswith('A IA do Gemini não está configurada'):
                from alertas.models import Alerta
                Alerta.objects.filter(
                    sensor_id=sensor_id, origem='tendencia', status='ativo'
                ).update(analise_ia=text)
        return response
