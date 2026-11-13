"""Regras determinísticas para priorização de ordens de serviço."""

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import OrdemServico


def registros_alerta(alerta):
    """Texto legível com os mesmos instantes preservados no histórico estruturado."""
    def horario(valor):
        data = parse_datetime(valor) if isinstance(valor, str) else valor
        return timezone.localtime(data).strftime('%d/%m/%Y %H:%M:%S %z')

    evidencia = alerta.dados_deteccao or {}
    rotulos = dict(alerta.NIVEL_CHOICES)
    inicial = evidencia.get('nivel')
    nivel = rotulos.get(inicial, 'inicial não registrado')
    registros = [(
        f'[ABERTURA DO ALERTA #{alerta.pk} · {horario(alerta.data_alerta)}] '
        f'Nível {nivel}.\n{evidencia.get("descricao") or alerta.descricao}'
    )]
    for evento in alerta.historico_niveis or []:
        registros.append(
            f'[ELEVAÇÃO DO ALERTA #{alerta.pk} · {horario(evento["ocorrido_em"])} · '
            f'{rotulos.get(evento["nivel_anterior"], evento["nivel_anterior"])} → '
            f'{rotulos.get(evento["nivel"], evento["nivel"])}]\n{evento["descricao"]}'
        )
    return registros


def acrescentar_registros_alerta(ordem, alerta):
    for registro in registros_alerta(alerta):
        # O cabeçalho contém ID, instante e transição; repetir análise não duplica.
        if registro.split('\n', 1)[0] not in ordem.descricao:
            ordem.descricao += '\n\n' + registro


def evidencia_previsao_abertura(alerta, dados):
    """Captura a análise elegível da criação da ordem, não a detecção anterior."""
    from alertas.evidence import detection_snapshot

    evidencia = detection_snapshot(alerta.sensor, 'tendencia', alerta.tipo_alerta,
                                   alerta.nivel, alerta.descricao, dados)
    # Vínculos operacionais não pertencem à evidência matemática da abertura.
    for field in ('predictive_work_order', 'limit_alert', 'active_alert_id'):
        evidencia['analise'].pop(field, None)
    at = parse_datetime(dados.get('projected_breach_at') or '')
    horario = timezone.localtime(at).strftime('%d/%m/%Y às %H:%M:%S %z') if at else 'horário não registrado'
    unit = evidencia['unidade_medida']
    antecedencia = dados.get('config_used', {}).get('antecedencia_os_minutos')
    evidencia.update(
        registrado_em=timezone.now().isoformat(),
        resumo=(f'Abertura automática: tendência confirmada prevê atingir '
                f'{evidencia["limite_operacional"]:g} {unit} em {horario}, '
                f'dentro da antecedência configurada de {antecedencia} min. '
                'Inspecionar o equipamento; a projeção não representa uma data de quebra.'),
    )
    return evidencia


class PrioridadeOSService:
    """A classe vigente do equipamento é copiada uma única vez na abertura."""

    @classmethod
    def calcular(cls, equipamento, tipo_os=None, gravidade='ausente', risco_seguranca=False, prioridade_plano=None):
        classe = equipamento.criticidade if equipamento.criticidade in ('A', 'B', 'C') else None
        motivo = (f'Prioridade {classe}: criticidade do equipamento na abertura.' if classe
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
        descricao = '\n\n'.join(registros_alerta(alerta))
        if ordem is None:
            return OrdemServico.objects.create(
                equipamento=alerta.equipamento, alerta_origem=alerta, sensor_origem=alerta.sensor,
                titulo=titulo, descricao=descricao, status='pendente', **dados,
            )
        peso_gravidade = {'ausente': 0, 'baixa': 1, 'moderada': 2, 'alta': 3, 'critica': 4}
        agravou = peso_gravidade[gravidade] > peso_gravidade[ordem.gravidade_condicao]
        descricao_anterior = ordem.descricao
        acrescentar_registros_alerta(ordem, alerta)
        if agravou or ordem.descricao != descricao_anterior:
            if agravou:
                ordem.gravidade_condicao = gravidade
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
        titulo = f'INSPEÇÃO PREDITIVA: previsão de atingir o limite · {alerta.sensor.nome if alerta.sensor else alerta.tipo_alerta}'
        descricao = (
            '\n\n'.join(registros_alerta(alerta)) + '\n'
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
                # Alertas legados podem não ter sensor nem evidências matemáticas.
                evidencia = evidencia_previsao_abertura(alerta, dados) if alerta.sensor_id else {}
                ordem = OrdemServico.objects.create(
                    equipamento=alerta.equipamento,
                    sensor_origem=alerta.sensor,
                    alerta_origem=alerta,
                    tipo_os='preditiva',
                    titulo=titulo,
                    descricao=(evidencia.get('resumo', '') + '\n\n' + descricao).strip(),
                    evidencia_preditiva=evidencia,
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
                acrescentar_registros_alerta(ordem, alerta)
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
