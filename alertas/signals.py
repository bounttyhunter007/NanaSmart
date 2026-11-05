from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Alerta
from manutencao.services import PrioridadeOSService

@receiver(post_save, sender=Alerta)
def vincular_ordem_servico_ao_alerta(sender, instance, created, raw=False, **kwargs):
    """
    Encaminha ocorrências ativas ao serviço, sem encerrar ordens na recuperação.
    """
    # Só processa se o alerta estiver ativo e for novo ou escalado
    if raw or instance.status != 'ativo':
        return

    if instance.origem == 'tendencia':
        ordem = PrioridadeOSService.criar_por_tendencia(instance)
    else:
        ordem = PrioridadeOSService.criar_por_alerta(instance)
    if ordem and instance.ordem_servico_id != ordem.pk:
        # Evita disparar novamente este sinal apenas para registrar o vínculo.
        Alerta.objects.filter(pk=instance.pk).update(ordem_servico=ordem)
        instance.ordem_servico_id = ordem.pk
