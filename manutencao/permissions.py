from rest_framework import permissions

class IsOwnerOrGestorOrUnassigned(permissions.BasePermission):
    """
    Regras de O.S.:
    1. Gestores e Admins: Acesso total.
    2. Técnicos:
       - Podem editar se forem o responsável.
       - Podem editar se a O.S. não tiver responsável (para poder "pegar" a tarefa).
       - NÃO podem editar O.S. que já pertence a outro técnico.
       - NÃO podem atribuir uma O.S. para outra pessoa (apenas para si mesmos).
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Gestores e Admins sempre têm acesso
        if user.tipo_usuario in ['gestor', 'admin'] or user.is_superuser:
            return True

        # Técnicos
        if user.tipo_usuario == 'tecnico':
            # Se a O.S. já tem um responsável e não é o usuário logado
            if obj.responsavel and obj.responsavel != user:
                return False
            
            # Se for uma tentativa de edição (PUT/PATCH)
            if request.method in ['PUT', 'PATCH']:
                # Se o técnico tentar mudar o responsável para outra pessoa que não seja ele mesmo
                novo_responsavel_id = request.data.get('responsavel')
                if novo_responsavel_id and int(novo_responsavel_id) != user.id:
                    return False

            return True

        return False
