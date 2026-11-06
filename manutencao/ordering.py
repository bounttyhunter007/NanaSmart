from django.db.models import Case, When, IntegerField


def prioridade_rank():
    return Case(When(prioridade='A', then=0), When(prioridade='B', then=1),
                When(prioridade='C', then=2), default=3, output_field=IntegerField())


def ordenar_ordens(queryset):
    return queryset.annotate(priority_rank=prioridade_rank()).order_by('priority_rank', 'data_abertura', 'pk')
