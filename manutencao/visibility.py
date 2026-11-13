"""Escopo compartilhado entre atendimento e acompanhamento de ordens."""
from django.db.models import Q

from .models import OrdemServico


def visible_work_orders(user, queryset=None):
    qs = OrdemServico.objects.all() if queryset is None else queryset
    if user.tipo_usuario == 'admin':
        return qs
    if not user.empresa_id:
        return qs.none()
    qs = qs.filter(equipamento__empresa_id=user.empresa_id)
    if user.tipo_usuario == 'tecnico':
        qs = qs.filter(Q(responsavel=user) | Q(responsavel__isnull=True))
    return qs
