from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Equipamento


@receiver(post_save, sender=Equipamento)
def verificar_planos_por_horimetro(sender, instance, **kwargs):
    """
    Sempre que o horímetro de um equipamento for atualizado,
    percorre todos os planos ativos e verifica se algum limiar foi cruzado.
    Se sim, cria uma O.S. Preditiva automaticamente.
    """
    # Importação local para evitar circular imports
    from manutencao.models import OrdemServico

    for plano in instance.planos_manutencao.filter(ativo=True):
        proximo_disparo = plano.horimetro_ultima_os + plano.intervalo_horas

        # Horímetro atual ainda não atingiu o próximo disparo
        if instance.horimetro < proximo_disparo:
            continue

        # Verifica se já existe uma O.S. preditiva aberta para este plano específico
        ja_existe = OrdemServico.objects.filter(
            equipamento=instance,
            tipo_os='preditiva',
            titulo__contains=plano.nome_servico,
            status__in=['pendente', 'andamento']
        ).exists()

        if ja_existe:
            continue  # Não duplica

        # 🚀 DISPARO: Cria a O.S. preditiva
        OrdemServico.objects.create(
            equipamento=instance,
            titulo=f"[PREDITIVA] {plano.nome_servico}",
            descricao=(
                f"Manutenção preditiva programada por horímetro.\n"
                f"Plano: {plano.nome_servico}\n"
                f"Horímetro de disparo: {instance.horimetro:.1f}h\n"
                f"Intervalo do plano: a cada {plano.intervalo_horas:.0f}h\n\n"
                f"Detalhes do serviço:\n{plano.descricao}"
            ),
            tipo_os='preditiva',
            prioridade=plano.prioridade,
            status='pendente',
        )

        # Atualiza o registro do plano para o próximo ciclo
        plano.horimetro_ultima_os = instance.horimetro
        plano.save(update_fields=['horimetro_ultima_os'])
