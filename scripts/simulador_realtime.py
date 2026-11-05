"""Telemetria ao vivo pelo fluxo real de ingestão, alertas e manutenção.

Execute --help para filtros e cenários. Não cria cadastros nem altera o esquema.
"""

import argparse
import logging
import math
import os
from pathlib import Path
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

logger = logging.getLogger('simulador_realtime')


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--interval-min', type=float, default=1.0)
    parser.add_argument('--interval-max', type=float, default=3.0)
    parser.add_argument('--cycles', type=int, default=0, help='0 = contínuo')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--sensor', type=int, nargs='+', help='IDs dos sensores')
    parser.add_argument('--equipamento', type=int, nargs='+', help='IDs dos equipamentos')
    parser.add_argument('--empresa', type=int, nargs='+', help='IDs das empresas')
    parser.add_argument('--cenario', choices=['normal', 'misto', 'baixo', 'medio', 'critico',
                                              'recuperacao', 'escalada'], default='misto',
                        help='Escalada repete normal → baixo → médio → crítico → recuperação')
    parser.add_argument('--fase-ciclos', type=int, default=8, help='Ciclos por fase da escalada')
    parser.add_argument('--chance-anomalia', type=float, default=0.01,
                        help='Probabilidade por sensor/ciclo no cenário misto (0 a 1)')
    parser.add_argument('--max-falhas', type=int, default=5,
                        help='Encerra após este número de ciclos consecutivos com falha')
    parser.add_argument('--dry-run', action='store_true', help='Consulta e simula sem gravar')
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args(argv)
    if any(not math.isfinite(v) or v <= 0 for v in (args.interval_min, args.interval_max)):
        parser.error('Os intervalos devem ser finitos e maiores que zero.')
    if args.interval_min > args.interval_max:
        parser.error('--interval-min não pode superar --interval-max.')
    if args.cycles < 0 or args.fase_ciclos < 1 or args.max_falhas < 1:
        parser.error('Ciclos devem ser >= 0; fase-ciclos e max-falhas devem ser >= 1.')
    if not math.isfinite(args.chance_anomalia) or not 0 <= args.chance_anomalia <= 1:
        parser.error('--chance-anomalia deve estar entre 0 e 1.')
    if any(i <= 0 for ids in (args.sensor, args.equipamento, args.empresa) if ids for i in ids):
        parser.error('IDs devem ser positivos.')
    return args


def configurar_logging(debug=False):
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S'))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False


def obter_sensores_ativos(sensor_ids=None, equipamento_ids=None, empresa_ids=None):
    from telemetria.models import Sensor
    qs = Sensor.objects.filter(ativo=True, equipamento__status='ativo').select_related('equipamento')
    for campo, ids in [('pk', sensor_ids), ('equipamento_id', equipamento_ids),
                       ('equipamento__empresa_id', empresa_ids)]:
        if ids:
            qs = qs.filter(**{f'{campo}__in': ids})
    return qs.order_by('equipamento_id', 'pk')


def limites_sensor(sensor):
    """Mesmos padrões e fronteiras inclusivas do serviço de alertas."""
    limite = sensor.limite_alerta
    percentuais = tuple(getattr(sensor, f'limite_alerta_{nivel}_pct')
                        if getattr(sensor, f'limite_alerta_{nivel}_pct') is not None else padrao
                        for nivel, padrao in [('baixo', 70.), ('medio', 85.), ('critico', 100.)])
    if limite is None or not math.isfinite(limite) or limite <= 0:
        raise ValueError('limite operacional deve ser finito e positivo')
    if not all(math.isfinite(p) for p in percentuais) or not 0 <= percentuais[0] < percentuais[1] < percentuais[2] <= 100:
        raise ValueError('percentuais devem obedecer 0 <= baixo < médio < crítico <= 100')
    return tuple(limite * p / 100 for p in percentuais)


def carregar_ultimo_valor_por_sensor(sensores):
    from django.db.models import OuterRef, Subquery
    from telemetria.models import Sensor, Telemetria
    ultima = Telemetria.objects.filter(sensor_id=OuterRef('pk')).order_by('-timestamp', '-pk')
    return dict(Sensor.objects.filter(pk__in=[s.pk for s in sensores]).annotate(
        ultimo=Subquery(ultima.values('valor')[:1])).values_list('pk', 'ultimo'))


def inicializar_memoria_sensores(sensores, memoria_atual):
    novos = [s for s in sensores if s.pk not in memoria_atual]
    historico = carregar_ultimo_valor_por_sensor(novos) if novos else {}
    memoria = {}
    for sensor in sensores:
        valor = memoria_atual.get(sensor.pk, historico.get(sensor.pk))
        if valor is None or not math.isfinite(valor):
            valor = limites_sensor(sensor)[0] * .8
        memoria[sensor.pk] = valor
    return memoria


def fase_cenario(cenario, ciclo, fase_ciclos):
    if cenario != 'escalada':
        return cenario
    fases = ('normal', 'baixo', 'medio', 'critico', 'recuperacao')
    return fases[((ciclo - 1) // fase_ciclos) % len(fases)]


def gerar_valor_sensor(sensor, valor_anterior, rng=None, cenario='misto', chance_anomalia=.01):
    rng = rng or random
    baixo, medio, critico = limites_sensor(sensor)
    if cenario == 'misto':
        cenario = rng.choice(('baixo', 'medio', 'critico')) if rng.random() < chance_anomalia else 'normal'
    faixas = {'normal': (baixo * .65, baixo * .95),
              'recuperacao': (baixo * .65, baixo * .90),
              'baixo': (baixo, medio), 'medio': (medio, critico),
              'critico': (critico, critico + sensor.limite_alerta * .15)}
    minimo, maximo = faixas[cenario]
    # Margem interna evita cruzar níveis por arredondamento. Não arredondar o dado
    # persistido: sensores de pequena escala também precisam manter sua precisão.
    margem = (maximo - minimo) * .05
    alvo = rng.uniform(minimo + margem, maximo - margem)
    # Temperatura/umidade respondem lentamente; corrente e vibração têm
    # maior variabilidade. Os limites sempre vêm do cadastro, não do tipo.
    resposta, ruido = {
        'temperatura': (.12, .015), 'umidade': (.08, .01),
        'pressao': (.25, .03), 'corrente': (.40, .05),
        'vibracao': (.50, .07),
    }.get(sensor.tipo, (.25, .04))
    valor = valor_anterior + (alvo - valor_anterior) * resposta + rng.uniform(-1, 1) * (maximo - minimo) * ruido
    valor = min(maximo - margem, max(minimo + margem, valor))
    return valor, critico, minimo, maximo


def rodar_ciclo(sensores, memoria_valores, dry_run=False, rng=None, cenario='misto', chance_anomalia=.01):
    from django.db import DatabaseError, transaction
    from telemetria.models import Sensor, Telemetria
    criadas = simuladas = falhas = ignoradas = 0
    for sensor in sensores:
        valor, critico, minimo, maximo = gerar_valor_sensor(
            sensor, memoria_valores[sensor.pk], rng, cenario, chance_anomalia)
        if not dry_run:
            try:
                # Um sensor com erro não desfaz os demais. Save e sinais continuam
                # no fluxo oficial (bulk_create pularia os alertas e tendências).
                with transaction.atomic():
                    atual = Sensor.objects.select_for_update().select_related('equipamento').get(pk=sensor.pk)
                    if not atual.ativo or atual.equipamento.status != 'ativo':
                        ignoradas += 1
                        continue
                    if limites_sensor(atual) != limites_sensor(sensor):
                        ignoradas += 1
                        continue  # configuração mudou: atualizar no próximo ciclo
                    Telemetria.objects.create(sensor=atual, valor=valor)
                criadas += 1
            except Sensor.DoesNotExist:
                ignoradas += 1
                continue
            except DatabaseError:
                falhas += 1
                logger.exception('Falha na gravação do sensor %s; memória preservada.', sensor.pk)
                continue
        else:
            simuladas += 1
        memoria_valores[sensor.pk] = valor
        logger.debug('%s | sensor=%s %s | %.6g %s | faixa %.6g–%.6g; crítico %.6g',
                     sensor.equipamento.nome, sensor.pk, sensor.nome, valor,
                     sensor.unidade_medida, minimo, maximo, critico)
    return {'gravadas': criadas, 'simuladas': simuladas, 'falhas': falhas, 'ignoradas': ignoradas}


def verificar_banco():
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    executor = MigrationExecutor(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        raise RuntimeError('Há migrações pendentes. Execute python manage.py migrate antes de simular.')
    logger.info('Banco: %s | %s | host=%s', connection.vendor, connection.settings_dict['NAME'],
                connection.settings_dict.get('HOST') or 'local')


def run_simulator(args):
    from django.db import OperationalError, InterfaceError, close_old_connections, connections
    configurar_logging(args.debug)
    rng = random.Random(args.seed)
    espera = random.Random(args.seed)  # cadência não interfere na sequência dos valores
    memoria = {}
    concluidos = consecutivas = total = erros = 0
    try:
        verificar_banco()
        logger.info('Iniciando cenário=%s dry_run=%s empresa=%s equipamento=%s sensor=%s',
                    args.cenario, args.dry_run, args.empresa, args.equipamento, args.sensor)
        while not args.cycles or concluidos < args.cycles:
            inicio = time.monotonic()
            falhou = False
            try:
                close_old_connections()
                sensores = list(obter_sensores_ativos(args.sensor, args.equipamento, args.empresa))
                validos = []
                for sensor in sensores:
                    try:
                        limites_sensor(sensor)
                    except ValueError as exc:
                        logger.error('Sensor %s ignorado: %s', sensor.pk, exc)
                        falhou = True
                    else:
                        validos.append(sensor)
                memoria = inicializar_memoria_sensores(validos, memoria)
                fase = fase_cenario(args.cenario, concluidos + 1, args.fase_ciclos)
                resumo = rodar_ciclo(validos, memoria, args.dry_run, rng, fase, args.chance_anomalia)
                falhou |= resumo['falhas'] > 0
                total += resumo['gravadas']
                erros += resumo['falhas']
                logger.info('Ciclo %s | fase=%s sensores=%s | %s', concluidos + 1, fase, len(validos), resumo)
                if not sensores:
                    logger.warning('Nenhum sensor ativo corresponde aos filtros; aguardando cadastros/ativação.')
            except (OperationalError, InterfaceError):
                logger.exception('Banco indisponível; nova tentativa no próximo ciclo.')
                connections.close_all()
                falhou = True
                erros += 1
            concluidos += 1
            consecutivas = consecutivas + 1 if falhou else 0
            if consecutivas >= args.max_falhas:
                logger.error('Limite de %s ciclos consecutivos com falha atingido.', args.max_falhas)
                return 1
            if args.cycles and concluidos >= args.cycles:
                break
            time.sleep(max(0, espera.uniform(args.interval_min, args.interval_max) - (time.monotonic() - inicio)))
        return 1 if consecutivas else 0
    except KeyboardInterrupt:
        logger.info('Interrompido pelo operador.')
        return 130
    except Exception:
        logger.exception('Simulação encerrada por erro.')
        return 1
    finally:
        connections.close_all()
        logger.info('Finalizado: %s ciclos, %s leituras gravadas, %s erros de banco.', concluidos, total, erros)


def main(argv=None):
    args = parse_args(argv)  # --help e argumentos inválidos não precisam do Django/banco
    import django
    django.setup()
    return run_simulator(args)


if __name__ == '__main__':
    sys.exit(main())
