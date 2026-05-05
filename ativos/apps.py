from django.apps import AppConfig


class AtivosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ativos'

    def ready(self):
        import ativos.signals  # noqa: F401
