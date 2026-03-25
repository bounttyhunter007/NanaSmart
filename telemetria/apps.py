from django.apps import AppConfig


class TelemetriaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telemetria'

    def ready(self):
        import telemetria.signals
