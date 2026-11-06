"""Regras determinísticas para priorização de ordens de serviço."""

from django.db import transaction
from .models import OrdemServico


class PrioridadeOSService:
    """A classe vigente do equipamento é copiada uma única vez na abertura."""

    @classmethod
    def calcular(cls, equipamento, tipo_os=None, gravidade='ausente', risco_seguranca=False, prioridade_plano=None):
        classe = equipamento.criticidade if equipamento.criticidade in ('A', 'B', 'C') else None
        motivo = (f'Prioridade {classe} herdada da criticidade do equipamento na abertura.' if classe
                  else 'A definir: equipamento sem criticidade avaliada na abertura; requer triagem do gestor.')
        return classe, motivo, classe

    @classmethod
    def preencher(cls, dados, equipamento, prioridade_plano=None):
        prioridade, justificativa, criticidade = cls.calcular(equipamento)
        dados.update({
            'prioridade': prioridade, 'prioridade_automatica': prioridade,
            'prioridade_origem': 'herdada', 'prioridade_herdada_conhecida': True,
            'justificativa_prioridade': justificativa, 'criticidade_na_abertura': criticidade,
            'justificativa_criticidade_na_abertura': equipamento.justificativa_criticidade or '',
            'criterios_criticidade_na_abertura_id': equipamento.criterios_criticidade_id,
            'prioridade_manual': False,
        })
        return dados

    @classmethod
    @transaction.atomic
    def criar_por_alerta(cls, alerta):
        from alertas.models import Alerta
        from telemetria.models import Sensor

        if alerta.origem == 'limite' and alerta.sensor_id:
            Sensor.objects.select_for_update().get(pk=alerta.sensor_id)
        alerta = Alerta.objects.select_for_update().get(pk=alerta.pk)
        if alerta.status != 'ativo':
            return None
        gravidade = {'baixo': 'baixa', 'medio': 'moderada', 'critico': 'critica'}[alerta.nivel]
        titulo = f'MANUTENÇÃO: {alerta.tipo_alerta}'
        ordem = OrdemServico.objects.select_for_update().filter(pk=alerta.ordem_servico_id).first()
        if ordem is None:
            ordem = OrdemServico.objects.select_for_update().filter(alerta_origem=alerta).first()
        # Uma recorrência usa o trabalho ainda aberto do MESMO sensor.
        # Alertas manuais são ocorrências próprias e não se agrupam pelo título.
        if ordem is None and alerta.origem == 'limite' and alerta.sensor_id:
            ordem = OrdemServico.objects.select_for_update().filter(
                equipamento_id=alerta.equipamento_id, sensor_origem_id=alerta.sensor_id,
                tipo_os='corretiva', alerta_origem__origem='limite',
                status__in=['pendente', 'andamento'],
            ).order_by('pk').first()
        if ordem and ordem.status in ('concluida', 'cancelada'):
            return ordem
        dados = cls.preencher({
            'tipo_os': 'corretiva', 'gravidade_condicao': gravidade, 'risco_seguranca': False,
        }, alerta.equipamento)
        descricao = f'O.S. vinculada ao alerta: {alerta.tipo_alerta}.\n{alerta.descricao}'
        if ordem is None:
            return OrdemServico.objects.create(
                equipamento=alerta.equipamento, alerta_origem=alerta, sensor_origem=alerta.sensor,
                titulo=titulo, descricao=descricao, status='pendente', **dados,
            )
        peso_gravidade = {'ausente': 0, 'baixa': 1, 'moderada': 2, 'alta': 3, 'critica': 4}
        agravou = peso_gravidade[gravidade] > peso_gravidade[ordem.gravidade_condicao]
        nova_ocorrencia = alerta.ordem_servico_id != ordem.pk and ordem.alerta_origem_id != alerta.pk
        if agravou or nova_ocorrencia:
            if agravou:
                ordem.gravidade_condicao = gravidade
            ordem.descricao += f'\n\n[ATUALIZAÇÃO DO ALERTA #{alerta.pk}] {alerta.descricao}'
            ordem.save()
        return ordem

    @classmethod
    def criar_por_tendencia(cls, alerta):
        """Cria ou atualiza a única OS aberta do episódio de tendência.

        A relação OneToOne com o alerta é a chave de idempotência operacional:
        análises repetidas atualizam a mesma ordem e um episódio resolvido pode
        gerar uma nova ordem no futuro por estar associado a outro alerta.
        """
        if alerta.status != 'ativo':
            return None

        dados = alerta.dados_analise or {}
        if not dados.get('intervention_recommended'):
            return None

        gravidade = {
            'baixo': 'baixa', 'medio': 'moderada',
            'alto': 'alta', 'critico': 'critica',
        }.get(dados.get('risk_level'), 'moderada')
        prioridade, justificativa, criticidade = cls.calcular(
            alerta.equipamento, 'preditiva', gravidade,
        )
        titulo = f'MANUTENÇÃO PREDITIVA: {alerta.tipo_alerta}'
        descricao = (
            f'Intervenção preditiva vinculada ao alerta #{alerta.id}.\n'
            f'{alerta.descricao}\n'
            f'Indicadores: inclinação {dados.get("slope_per_hour")} por hora; '
            f'leituras analisadas: {dados.get("readings_count")}; '
            f'projeção até o limite: {dados.get("projected_breach_hours")} horas.'
        )
        with transaction.atomic():
            # Bloquear o alerta também protege a criação quando ainda não há OS.
            from alertas.models import Alerta
            Alerta.objects.select_for_update().get(pk=alerta.pk)
            ordem = (
                OrdemServico.objects.select_for_update()
                .filter(alerta_origem=alerta)
                .first()
            )
            if ordem is None:
                ordem = OrdemServico.objects.create(
                    equipamento=alerta.equipamento,
                    sensor_origem=alerta.sensor,
                    alerta_origem=alerta,
                    tipo_os='preditiva',
                    titulo=titulo,
                    descricao=descricao,
                    status='pendente',
                    prioridade=prioridade,
                    gravidade_condicao=gravidade,
                    prioridade_automatica=prioridade,
                    justificativa_prioridade=justificativa,
                    criticidade_na_abertura=criticidade,
                    justificativa_criticidade_na_abertura=(
                        alerta.equipamento.justificativa_criticidade or ''
                    ),
                )
            elif ordem.status in ('pendente', 'andamento'):
                ordem.gravidade_condicao = gravidade
                ordem.descricao = descricao
                ordem.save(update_fields=[
                    'gravidade_condicao', 'descricao',
                ])
        return ordem


@transaction.atomic
def alterar_prioridade(ordem, usuario, justificativa, prioridade=None, restaurar=False):
    from rest_framework.exceptions import ValidationError, PermissionDenied
    from .models import HistoricoPrioridadeOS
    if usuario.tipo_usuario not in ('admin', 'gestor'):
        raise PermissionDenied('Somente gestor ou administrador pode ajustar a prioridade.')
    ordem = OrdemServico.objects.select_for_update().get(pk=ordem.pk)
    if usuario.tipo_usuario != 'admin' and ordem.equipamento.empresa_id != usuario.empresa_id:
        raise PermissionDenied('A OS deve pertencer à sua empresa.')
    if ordem.status not in ('pendente', 'andamento'):
        raise ValidationError({'prioridade': 'Uma OS encerrada não pode mudar de prioridade.'})
    justificativa = (justificativa or '').strip()
    if not justificativa:
        raise ValidationError({'justificativa': 'Informe o motivo da alteração.'})
    if restaurar:
        if not ordem.prioridade_herdada_conhecida:
            raise ValidationError({'prioridade': 'A herança da OS legada não é conhecida. Faça um ajuste explícito.'})
        prioridade = ordem.prioridade_automatica
    elif prioridade not in ('A', 'B', 'C'):
        raise ValidationError({'prioridade': 'Use A, B ou C.'})
    anterior = ordem.prioridade
    dados = {'origem': ordem.prioridade_origem, 'justificativa': ordem.justificativa_prioridade,
             'prioridade_manual': ordem.prioridade_manual}
    ordem.prioridade = prioridade
    ordem.prioridade_manual = not restaurar
    ordem.prioridade_origem = 'herdada' if restaurar else 'ajustada'
    ordem.justificativa_prioridade = justificativa
    ordem.save(update_fields=['prioridade', 'prioridade_manual', 'prioridade_origem', 'justificativa_prioridade'])
    HistoricoPrioridadeOS.objects.create(ordem_servico=ordem, prioridade_anterior=anterior,
        prioridade_nova=prioridade, justificativa=justificativa,
        origem='restauracao' if restaurar else 'ajuste', alterado_por=usuario, dados_anteriores=dados)
    return ordem
