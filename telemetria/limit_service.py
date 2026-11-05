"""Ciclo de ocorrências por limite, independente da execução da manutenção."""

import math

from django.db import transaction

from alertas.models import Alerta
from .models import Sensor


# Duas observações são o mínimo para rejeitar uma normalização isolada.
# Critério acadêmico por amostras; não representa um período de estabilidade.
LEITURAS_NORMAIS_PARA_RECUPERACAO = 2
PESO_NIVEL = {'baixo': 1, 'medio': 2, 'critico': 3}


@transaction.atomic
def sync_limit_reading(leitura):
    sensor = Sensor.objects.select_for_update().get(pk=leitura.sensor_id)
    if (not sensor.ativo or sensor.limite_alerta is None or sensor.limite_alerta <= 0
            or not math.isfinite(sensor.limite_alerta) or not math.isfinite(leitura.valor)):
        return None

    percentual = leitura.valor / sensor.limite_alerta * 100
    baixo = sensor.limite_alerta_baixo_pct if sensor.limite_alerta_baixo_pct is not None else 70.0
    medio = sensor.limite_alerta_medio_pct if sensor.limite_alerta_medio_pct is not None else 85.0
    critico = sensor.limite_alerta_critico_pct if sensor.limite_alerta_critico_pct is not None else 100.0
    nivel = ('critico' if percentual >= critico else 'medio' if percentual >= medio
             else 'baixo' if percentual >= baixo else None)
    chave = f'limite:{sensor.pk}'
    ultimo = Alerta.objects.select_for_update().filter(
        sensor=sensor, origem='limite', evento_chave=chave,
    ).order_by('-pk').first()
    dados = dict(ultimo.dados_analise or {}) if ultimo else {}
    if dados.get('ultima_leitura_id', 0) >= leitura.pk:
        return ultimo

    em_observacao = ultimo and (
        ultimo.status == 'ativo'
        or (ultimo.status == 'ignorado' and not dados.get('recuperado_em'))
    )
    if not em_observacao:
        if nivel is None:
            return None
        ultimo = None
        dados = {}

    limites = {'baixo': baixo, 'medio': medio, 'critico': critico}
    if dados.get('limites_pct') != limites or dados.get('limite_operacional') != sensor.limite_alerta:
        dados['leituras_normais_consecutivas'] = 0

    dados.update({
        'ultima_leitura_id': leitura.pk,
        'ultimo_valor': leitura.valor,
        'ultimo_percentual': round(percentual, 4),
        'nivel_atual': nivel or 'normal',
        'ultima_leitura_em': leitura.timestamp.isoformat(),
        'limites_pct': limites,
        'limite_operacional': sensor.limite_alerta,
    })
    if nivel is None:
        dados['leituras_normais_consecutivas'] = dados.get('leituras_normais_consecutivas', 0) + 1
        if dados['leituras_normais_consecutivas'] >= LEITURAS_NORMAIS_PARA_RECUPERACAO:
            dados['recuperado_em'] = leitura.timestamp.isoformat()
            if ultimo.status == 'ativo':
                ultimo.status = 'resolvido'
    else:
        dados['leituras_normais_consecutivas'] = 0
        maximo = dados.get('nivel_maximo', ultimo.nivel if ultimo else nivel)
        dados['nivel_maximo'] = max((maximo, nivel), key=PESO_NIVEL.__getitem__)

    descricao = (
        f'Condição em {sensor.equipamento.nome}. Sensor {sensor.nome} '
        f'({sensor.get_tipo_display()}) registrou {leitura.valor}{sensor.unidade_medida} '
        f'({round(percentual, 1)}% do limite de {sensor.limite_alerta}{sensor.unidade_medida}).'
    )
    if ultimo is None:
        return Alerta.objects.create(
            equipamento=sensor.equipamento, sensor=sensor, origem='limite',
            evento_chave=chave, tipo_alerta=f'Alerta de {sensor.get_tipo_display()}',
            nivel=nivel, descricao=descricao, dados_analise=dados,
            data_ultima_analise=leitura.timestamp,
        )
    ultimo.nivel = dados.get('nivel_maximo', ultimo.nivel)
    ultimo.descricao = descricao
    ultimo.dados_analise = dados
    ultimo.data_ultima_analise = leitura.timestamp
    ultimo.save(update_fields=['nivel', 'descricao', 'dados_analise', 'data_ultima_analise', 'status'])
    return ultimo
