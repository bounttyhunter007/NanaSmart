from rest_framework import permissions

from .permission_policies import PermissionPolicyFactory


class IsGestor(permissions.BasePermission):
    """Permite acesso total apenas para Gestores ou Admins."""

    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('gestor')
        return policy.can_access(request.user, request.method)


class IsTecnico(permissions.BasePermission):
    """Permite acesso para Técnicos."""

    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('tecnico')
        return policy.can_access(request.user, request.method)


class IsGestorOrReadOnly(permissions.BasePermission):
    """Gestores podem tudo. Técnicos/Outros apenas leitura."""

    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('gestor_or_readonly')
        return policy.can_access(request.user, request.method)


class IsAuthenticatedNoDeleteForTecnico(permissions.BasePermission):
    """Usuários autenticados podem consultar recursos. Técnicos não podem deletar."""

    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('authenticated_no_delete_for_tecnico')
        return policy.can_access(request.user, request.method)
