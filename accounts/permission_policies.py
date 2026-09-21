from abc import ABC, abstractmethod


class BasePermissionPolicy(ABC):
    """Contrato base para políticas de acesso por perfil."""

    @abstractmethod
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        raise NotImplementedError


class GestorPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return user.tipo_usuario in ['gestor', 'admin'] or getattr(user, 'is_superuser', False)


class TecnicoPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return user.tipo_usuario == 'tecnico'


class GestorOrReadOnlyPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False

        if method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        return user.tipo_usuario in ['gestor', 'admin'] or getattr(user, 'is_superuser', False)


class AuthenticatedNoDeleteForTecnicoPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False

        if method in ['GET', 'HEAD', 'OPTIONS']:
            return True

        if user.tipo_usuario == 'tecnico' and method == 'DELETE':
            return False

        return user.tipo_usuario in ['gestor', 'admin'] or getattr(user, 'is_superuser', False)


class PermissionPolicyFactory:
    """Fábrica simples para centralizar políticas por perfil de usuário."""

    _policies = {
        'gestor': GestorPolicy(),
        'tecnico': TecnicoPolicy(),
        'gestor_or_readonly': GestorOrReadOnlyPolicy(),
        'authenticated_no_delete_for_tecnico': AuthenticatedNoDeleteForTecnicoPolicy(),
    }

    @classmethod
    def create(cls, policy_name: str):
        try:
            return cls._policies[policy_name]
        except KeyError as exc:
            raise ValueError(f"Política de permissão não registrada: {policy_name}") from exc

    @classmethod
    def register(cls, policy_name: str, policy: BasePermissionPolicy):
        cls._policies[policy_name] = policy
