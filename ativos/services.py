from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import CriteriosCriticidade, Equipamento, HistoricoCriticidadeEquipamento

CRITERIOS_SUGERIDOS = {
    'criterio_a': 'Alta consequência: risco relevante à segurança ou ambiente, interrupção de operação essencial, sem redundância confiável ou recuperação difícil.',
    'criterio_b': 'Consequência intermediária: redução relevante de produção ou qualidade, contingência limitada e recuperação viável com planejamento.',
    'criterio_c': 'Consequência limitada: baixo impacto operacional, redundância confiável ou contorno disponível e recuperação simples.',
}


@transaction.atomic
def aplicar_criticidade(equipamento, criticidade, justificativa, usuario=None, origem='individual'):
    """Registra avaliação explícita; não altera OS já abertas."""
    anterior = Equipamento.objects.select_for_update().get(pk=equipamento.pk)
    justificativa = (justificativa or '').strip()
    if criticidade not in ('A', 'B', 'C', None):
        raise ValidationError({'criticidade': 'Use A, B, C ou null.'})
    if not justificativa:
        raise ValidationError({'justificativa_criticidade': 'Informe a justificativa da avaliação.'})
    criterios = CriteriosCriticidade.objects.filter(empresa_id=equipamento.empresa_id).first()
    if criticidade and not criterios:
        raise ValidationError({'criticidade': 'Cadastre os critérios validados da empresa antes de classificar.'})
    equipamento.criticidade = criticidade
    equipamento.criticidade_origem = origem if criticidade else 'nao_avaliada'
    equipamento.justificativa_criticidade = justificativa
    equipamento.criterios_criticidade = criterios
    equipamento.save(update_fields=['criticidade', 'criticidade_origem', 'justificativa_criticidade', 'criterios_criticidade'])
    HistoricoCriticidadeEquipamento.objects.create(
        equipamento=equipamento, criticidade_anterior=anterior.criticidade,
        criticidade_nova=criticidade, justificativa=justificativa,
        criterios_criticidade=criterios, origem=origem,
        dados_anteriores={'justificativa': anterior.justificativa_criticidade,
                         'criterios_criticidade': anterior.criterios_criticidade_id,
                         'origem': anterior.criticidade_origem},
        alterado_por=usuario if getattr(usuario, 'is_authenticated', False) else None,
    )
    return equipamento
