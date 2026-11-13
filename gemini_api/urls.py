from django.urls import path
from .views import (
    GeminiChatView,
    GeminiOsAnalysisView,
    GeminiUnassignedOrdersView,
    GeminiFinanceView,
    GeminiTrendAnalysisView,
    PromptConfigListView,
    PromptConfigDetailView,
    PromptConfigResetView,
    PromptAnaliseOSView,
    PromptAnaliseOSResetView,
)

urlpatterns = [
    path('chat/', GeminiChatView.as_view(), name='gemini_chat'),
    path('ordens/analise/', GeminiOsAnalysisView.as_view(), name='gemini_ordens_analise'),
    path('ordens/sem-atribuicao/', GeminiUnassignedOrdersView.as_view(), name='gemini_ordens_sem_atribuicao'),
    path('gestao/financeira/', GeminiFinanceView.as_view(), name='gemini_gestao_financeira'),
    path('tendencia/', GeminiTrendAnalysisView.as_view(), name='gemini_tendencia'),
    path('prompts/', PromptConfigListView.as_view(), name='gemini_prompts_list'),
    path('prompts/analise-os/', PromptAnaliseOSView.as_view(), name='gemini_prompt_analise_os'),
    path('prompts/analise-os/reset/', PromptAnaliseOSResetView.as_view(), name='gemini_prompt_analise_os_reset'),
    path('prompts/<int:pk>/', PromptConfigDetailView.as_view(), name='gemini_prompts_detail'),
    path('prompts/<int:pk>/reset/', PromptConfigResetView.as_view(), name='gemini_prompts_reset'),
]
