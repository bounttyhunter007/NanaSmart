from django.contrib.auth.models import UserManager


class UsuarioManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('tipo_usuario', 'admin')
        return super().create_superuser(username, email, password, **extra_fields)
