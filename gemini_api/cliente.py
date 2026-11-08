"""Compatibilidade das funções antigas com o contrato de adapter da aplicação."""

from dotenv import load_dotenv
from .adapters import get_ai_adapter

load_dotenv(override=True)


def get_gemini_client():
    """Retorna o cliente do SDK para integrações legadas que ainda o utilizam."""
    return get_ai_adapter().get_client()


def is_gemini_available():
    return get_ai_adapter().is_available()


def generate_content(
    system_instruction,
    user_prompt,
    history=None,
    model_candidates=None,
    temperature=0.4,
):
    return get_ai_adapter().generate_content(
        system_instruction=system_instruction,
        user_prompt=user_prompt,
        history=history,
        model_candidates=model_candidates,
        temperature=temperature,
    )


def get_media_quebras_equipamentos(name):
    if not is_gemini_available():
        return f"IA indisponível. Detalhes de quebra para o equipamento: {name}."

    prompt = f"""
Você é um analista de dados especializado em manutenção industrial.
Receba os dados de quebra de equipamentos e calcule para o equipamento '{name}':
1. Tempo médio de quebra
2. Equipamento que mais quebra
3. Quais técnicos mais fazem manutenção

Forneça uma descrição analítica resumida e clara sobre este equipamento.
"""

    try:
        response_text, _ = generate_content(
            system_instruction="Você é um analista de manutenção industrial.",
            user_prompt=prompt,
        )
        return response_text
    except Exception as error:
        return f"Erro ao gerar a descrição do equipamento '{name}': {error}"
