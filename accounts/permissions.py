from rest_framework import permissions


class IsGestor(permissions.BasePermission):
    """
    Permite acesso total apenas para Gestores ou Admins.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.tipo_usuario in ['gestor', 'admin'] or request.user.is_superuser


class IsTecnico(permissions.BasePermission):
    """
    Permite acesso para Técnicos (geralmente leitura ou ações específicas de OS).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.tipo_usuario == 'tecnico'


class IsGestorOrReadOnly(permissions.BasePermission):
    """
    Gestores podem tudo. Técnicos/Outros apenas leitura.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.tipo_usuario in ['gestor', 'admin'] or request.user.is_superuser


class IsAuthenticatedNoDeleteForTecnico(permissions.BasePermission):
    """
    Qualquer usuário autenticado pode GET, POST e PATCH/PUT.
    Técnicos NÃO podem DELETE — apenas Gestores e Admins podem deletar registros.

    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method == 'DELETE':
            return request.user.tipo_usuario in ['gestor', 'admin'] or request.user.is_superuser

        return True
