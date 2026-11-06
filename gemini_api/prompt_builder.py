from .prompt_builder_pattern import PromptBuilderConcreto
from .prompt_director import PromptDirector

def _truncate_lines(lines, max_lines=15):
    if len(lines) <= max_lines:
        return lines
    return lines[:max_lines] + [f"... ({len(lines) - max_lines} itens adicionais omitidos)"]


# ─── Original (default) prompt texts ────────────────────────────────────────
# These are the built-in defaults that are used when no custom prompt is set.

DEFAULTS = {}

DEFAULTS['system_instruction_tecnico'] = (
    'foco técnico de campo, análise de ordens de serviço e resolução prática de falhas, '
    'sem expor dados financeiros detalhados.'
)

DEFAULTS['system_instruction_gestor'] = (
    'foco em gestão de manutenção, desempenho operacional, priorização de ordens e '
    'impacto financeiro da manutenção.'
)

DEFAULTS['system_instruction_admin'] = (
    'visão estratégica de gestão de ativos, governança de manutenção e controle financeiro '
    'de toda a plataforma.'
)

DEFAULTS['chat_context'] = (
    "CONTEXTUALIZAÇÃO RÁPIDA:\n"
    "- Empresa: {company_name}\n"
    "- Total de equipamentos: {total_equipment}\n"
    "- Equipamentos ativos: {active_equipment} | em manutenção: {maintenance_equipment} | inativos: {inactive_equipment}\n"
    "- Ordens em aberto: {open_orders_count}\n"
    "- Ordens sem atribuição: {unassigned_orders_count}"
)

DEFAULTS['os_analysis'] = (
    "INSTRUÇÃO:\n"
    "Analise as ordens de serviço descritas acima e sugira os próximos passos práticos.\n"
    "Para técnicos, indique como priorizar, o que verificar no equipamento e quando escalar.\n"
    "Para gestores/admin, indique quais ordens devem receber atenção imediata e por quê."
)

DEFAULTS['unassigned_orders'] = (
    "INSTRUÇÃO:\n"
    "Avalie estas ordens e sugira critérios claros para atribuição e priorização.\n"
    "Se houver ordens críticas ou de alto risco, indique-as e explique por quê."
)

DEFAULTS['finance'] = (
    "INSTRUÇÃO:\n"
    "Baseado nesses números, indique melhorias de gestão de manutenção, redução de custos e prioridades de investimento.\n"
    "Explique quais métricas devem ser monitoradas e quais ações trazer para reduzir retrabalho e tempo de parada."
)

DEFAULTS['trend_analysis'] = (
    "INSTRUÇÃO:\n"
    "Analise a tendência do sensor descrita acima e forneça:\n"
    "1. **Diagnóstico**: Avaliação objetiva do comportamento do sensor e o que ele indica\n"
    "2. **Causa Provável**: Possíveis causas técnicas para esta tendência\n"
    "3. **Recomendações de Manutenção**: Ações práticas a serem tomadas, priorizadas por urgência\n\n"
    "Use linguagem técnica mas acessível. Se a tendência for estável e saudável, indique que o equipamento está operando normalmente."
)


def get_all_defaults():
    """Return a copy of the default prompt texts dictionary."""
    return dict(DEFAULTS)


def _get_custom_prompt(key):
    """Fetch custom prompt from DB. Returns None if not customized."""
    try:
        from .models import PromptConfig
        config = PromptConfig.objects.filter(key=key).first()
        if config and config.is_customized:
            return config.custom_text.strip()
    except Exception:
        pass
    return None


def _get_effective_text(key):
    """Return custom text if set, otherwise the default."""
    custom = _get_custom_prompt(key)
    return custom if custom else DEFAULTS.get(key, '')


def build_system_instruction(user, purpose):
    company_name = user.empresa.nome if getattr(user, 'empresa', None) else 'Todas as empresas'
    if user.tipo_usuario == 'tecnico':
        role = 'técnico'
        focus = _get_effective_text('system_instruction_tecnico')
    elif user.tipo_usuario == 'gestor':
        role = 'gestor'
        focus = _get_effective_text('system_instruction_gestor')
    else:
        role = 'administrador'
        focus = _get_effective_text('system_instruction_admin')

    return (
        f"Você é a NanaSmart AI, o assistente de manutenção industrial e gestão de ativos "
        f"para a empresa {company_name}. Seu papel é entregar respostas claras, objetivas e "
        f"acionáveis para um {role}."
        "\n\nDiretriz de escopo: responda apenas sobre manutenção, ordens de serviço, alertas, "
        "telemetria, desempenho de equipamentos e gestão de manutenção. Recuse perguntas "
        f"fora desse escopo. {focus}\n"
        f"\n\nObjetivo atual: {purpose}. "
        "Alertas são registros históricos automáticos de detecções, sem ações de resolver, ignorar, editar ou excluir. "
        "Os alertas do contexto são ocorrências das últimas 24 horas, não uma lista de problemas atuais. "
        "Use as leituras para analisar a condição atual e a O.S. vinculada para orientar o atendimento. "
        "Normalização do sensor não comprova conclusão da manutenção. Problemas humanos entram diretamente em uma O.S. "
        "Use sempre formatação Markdown com marcadores ou tópicos quando for útil."
    )


def build_chat_prompt(user, context, message):
    # Build contextualisation header (may be customized)
    custom_context = _get_custom_prompt('chat_context')
    if custom_context:
        context_str = custom_context.format(
            company_name=context['company_name'],
            total_equipment=context['total_equipment'],
            active_equipment=context['active_equipment'],
            maintenance_equipment=context['maintenance_equipment'],
            inactive_equipment=context['inactive_equipment'],
            open_orders_count=context['open_orders'].count(),
            unassigned_orders_count=context['unassigned_orders'].count(),
        )
    else:
        context_str = (
            "CONTEXTUALIZAÇÃO RÁPIDA:\n"
            f"- Empresa: {context['company_name']}\n"
            f"- Total de equipamentos: {context['total_equipment']}\n"
            f"- Equipamentos ativos: {context['active_equipment']} | em manutenção: {context['maintenance_equipment']} | inativos: {context['inactive_equipment']}\n"
            f"- Ordens em aberto: {context['open_orders'].count()}\n"
            f"- Ordens sem atribuição: {context['unassigned_orders'].count()}"
        )

    builder = PromptBuilderConcreto()
    prompt = PromptDirector.montar_chat(builder, context, context_str, message)
    return prompt.obter_texto()


def build_os_analysis_prompt(user, context, message):
    context_str = (
        "CONTEXTUALIZAÇÃO DE ORDENS DE SERVIÇO:\n"
        f"- Total de ordens em aberto: {context['open_orders'].count()}\n"
        f"- Ordens sem atribuição: {context['unassigned_orders'].count()}\n"
        f"- Ordens atribuídas a este técnico: {context['assigned_orders'].count() if user.tipo_usuario == 'tecnico' else 'não aplicável'}"
    )

    instruction = _get_effective_text('os_analysis')
    builder = PromptBuilderConcreto()
    prompt = PromptDirector.montar_analise_os(builder, context, context_str, instruction, message)
    return prompt.obter_texto()


def build_unassigned_orders_prompt(user, context, message):
    context_str = (
        "CONTEXTUALIZAÇÃO DE ORDENS NÃO ATRIBUÍDAS:\n"
        f"- Total de ordens sem atribuição: {context['unassigned_orders'].count()}"
    )

    instruction = _get_effective_text('unassigned_orders')
    builder = PromptBuilderConcreto()
    prompt = PromptDirector.montar_ordens_nao_atribuidas(builder, context, context_str, instruction, message)
    return prompt.obter_texto()


def build_finance_prompt(user, context, message):
    financial = context['financial_summary']
    context_str = (
        "CONTEXTUALIZAÇÃO FINANCEIRA:\n"
        f"- Custo total de manutenção registrado: R$ {financial['total_cost']:.2f}\n"
        f"- Média de custo por OS concluída: R$ {financial['average_cost_per_os']:.2f}\n"
        f"- Ordens concluídas com histórico financeiro: {financial['completed_orders']}"
    )

    instruction = _get_effective_text('finance')
    builder = PromptBuilderConcreto()
    prompt = PromptDirector.montar_financeiro(builder, context, context_str, instruction, message)
    return prompt.obter_texto()


def build_trend_analysis_prompt(user, context, message, trend_data=None):
    """
    Constrói prompt para análise de tendência de sensor com IA.
    trend_data: dict retornado por analyze_sensor_trend()
    """
    if not trend_data:
        return message

    sensor = trend_data.get('sensor_info', {})
    direction_labels = {
        'increasing': 'CRESCENTE ↑',
        'decreasing': 'DECRESCENTE ↓',
        'stable': 'ESTÁVEL →',
    }
    risk_labels = {
        'critico': '🔴 CRÍTICO',
        'alto': '🟠 ALTO',
        'medio': '🟡 MÉDIO',
        'baixo': '🟢 BAIXO',
    }

    blocks = [
        "O backend já calculou a tendência e o nível de risco. Não altere essa classificação.",
        "Use somente os dados abaixo; diferencie observações de hipóteses e informe limitações.",
        "DADOS DE TENDÊNCIA DO SENSOR:",
        f"- Sensor: {sensor.get('nome', '?')} ({sensor.get('tipo_display', '?')})",
        f"- Equipamento: {sensor.get('equipamento_nome', '?')}",
        f"- Unidade de medida: {sensor.get('unidade_medida', '?')}",
        f"- Direção da tendência: {direction_labels.get(trend_data.get('direction'), '?')}",
        f"- Variação por hora (slope): {trend_data.get('slope_per_hour', 0)} {sensor.get('unidade_medida', '')}/hora",
        f"- Valor atual: {trend_data.get('current_value', '?')} {sensor.get('unidade_medida', '')}",
        f"- Limite operacional: {sensor.get('limite_alerta', '?')} {sensor.get('unidade_medida', '')}",
        f"- Nível de risco calculado: {risk_labels.get(trend_data.get('risk_level'), '?')}",
    ]

    breach = trend_data.get('projected_breach_hours')
    if breach is not None:
        if breach == 0:
            blocks.append("- Projeção: ⚠️ LIMITE JÁ ULTRAPASSADO")
        else:
            blocks.append(f"- Projeção de violação do limite: {breach} horas")
    else:
        blocks.append("- Projeção de violação do limite: sem risco projetado")

    blocks.append(f"- Leituras analisadas: {trend_data.get('readings_count', 0)}")

    # Últimas leituras resumidas
    readings = trend_data.get('readings_summary', [])
    if readings:
        recent = readings[-10:]  # últimas 10
        readings_str = ", ".join([f"{r['valor']}" for r in recent])
        blocks.append(f"- Últimos valores: [{readings_str}]")

    instruction = _get_effective_text('trend_analysis')
    blocks += [f"\n{instruction}"]

    if message and message.strip():
        blocks += ["\nOBSERVAÇÃO ADICIONAL DO USUÁRIO:", message]

    return "\n".join(blocks)

