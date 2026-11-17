from rest_framework import permissions

from .permission_policies import PermissionPolicyFactory


class IsOperationalUser(permissions.BasePermission):
    """Recursos de manutenção reservados a técnico, gestor e administrador."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.tipo_usuario in ('admin', 'gestor', 'tecnico'))


class IsOperationalOrOperatorReadOnly(IsOperationalUser):
    """Operador consulta somente os recursos básicos que usam esta permissão."""

    def has_permission(self, request, view):
        if super().has_permission(request, view):
            return request.method in permissions.SAFE_METHODS or IsGestor().has_permission(request, view)
        user = request.user
        return bool(user and user.is_authenticated and user.tipo_usuario == 'operador'
                    and request.method in permissions.SAFE_METHODS)


class IsGestor(permissions.BasePermission):
    """Permite acesso total apenas para Gestores ou Admins."""

    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('gestor')
        return policy.can_access(request.user, request.method)


class IsCompanyManager(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.tipo_usuario == 'admin' or user.is_superuser:
            return True
        return user.tipo_usuario == 'gestor' and request.method not in ('POST', 'DELETE')

    def has_object_permission(self, request, view, obj):
        user = request.user
        return (
            user.tipo_usuario == 'admin'
            or user.is_superuser
            or obj.pk == user.empresa_id
        )


class IsTecnico(permissions.BasePermission):
    """Permite acesso para Técnicos."""

    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('tecnico')
        return policy.can_access(request.user, request.method)


class IsGestorOrReadOnly(permissions.BasePermission):
    """Gestores e admins escrevem; técnicos consultam; operadores sem acesso."""

    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('gestor_or_readonly')
        return policy.can_access(request.user, request.method)


class IsAuthenticatedNoDeleteForTecnico(permissions.BasePermission):
    """Admin, gestor e técnico consultam; somente gestor/admin escrevem."""

    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('authenticated_no_delete_for_tecnico')
        return policy.can_access(request.user, request.method)
