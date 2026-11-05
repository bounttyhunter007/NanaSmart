from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Telemetria
from .limit_service import sync_limit_reading
from .predictive_service import sync_sensor_trend


@receiver(post_save, sender=Telemetria)
def checar_limites_telemetria(sender, instance, created, raw=False, **kwargs):
    if raw or not created or not instance.sensor.ativo:
        return
    sync_sensor_trend(instance.sensor_id)
    sync_limit_reading(instance)
