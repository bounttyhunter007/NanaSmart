from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Telemetria
from alertas.models import Alerta

@receiver(post_save, sender=Telemetria)
def checar_limites_telemetria(sender, instance, created, **kwargs):
    if created:
        sensor = instance.sensor
        valor = instance.valor
        equipamento = sensor.equipamento

        # Lógica de exemplo: se a temperatura passar de 80 ou vibração passar de 10
        alerta_necessario = False
        tipo = ""
        nivel = "baixo"
        descricao = ""

        if sensor.tipo_sensor == 'temperatura' and valor > 80:
            alerta_necessario = True
            tipo = "Temperatura Excessiva"
            nivel = "critico"
            descricao = f"O sensor {sensor.id} detectou {valor}°C no equipamento {equipamento.nome}. Limite de 80°C excedido."
        
        elif sensor.tipo_sensor == 'vibracao' and valor > 10:
            alerta_necessario = True
            tipo = "Vibração Anômala"
            nivel = "medio"
            descricao = f"O sensor {sensor.id} detectou vibração de {valor} mm/s no equipamento {equipamento.nome}."

        if alerta_necessario:
            Alerta.objects.create(
                equipamento=equipamento,
                tipo_alerta=tipo,
                nivel=nivel,
                descricao=descricao
            )
