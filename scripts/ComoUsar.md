# Scripts na pasta `scripts`

Este documento descreve brevemente os scripts disponíveis em `scripts/` e como usá-los.

## 1. `seed_db.py`

**O que faz**
- Popula o banco de dados com dados falsos industriais realistas.
- Cria empresas, gestores, técnicos, equipamentos, sensores, planos de manutenção, telemetria, ordens de serviço e alertas.
- Gera histórico de telemetria e cronogramas de manutenção mais coesos para MTTR/MTBF.

**Como usar**
- Execute a partir da raiz do projeto:
  ```bash
  python scripts/seed_db.py --empresas 3 --equipamentos 8 --funcionarios 20
  ```
- Parâmetros disponíveis:
  - `--empresas`: número de empresas a criar (default: `2`)
  - `--equipamentos`: número de equipamentos por empresa (default: `10`)
  - `--funcionarios`: total de funcionários por empresa, incluindo o gestor (default: `1 gestor + 3 a 5 técnicos aleatórios`)
  - `--days`: dias de histórico de telemetria e manutenção (default: `120`)
  - `--clean-only`: apenas limpa o banco de dados sem popular

**Observações**
- O script já configura o ambiente Django automaticamente.
- Ele apaga dados existentes em `Empresa`, `Equipamento`, `Sensor`, `Telemetria`, `OrdemServico`, `HistoricoManutencao`, `Alerta` e outros modelos relacionados.
- Pode ser estendido para aceitar mais parâmetros, por exemplo:
  - número de técnicos por empresa
  - número de planos de manutenção por equipamento
  - nível de criticidade de ordens
  - quantidade e tipo de alertas

## 2. `simulador_realtime.py`

**O que faz**
- Simula geração contínua de leituras de telemetria para sensores ativos.
- Preserva histórico de valor para fazer transições suaves.
- Permite filtrar por sensor ou por equipamento.
- Executa em ciclos com intervalos aleatórios entre valores mínimo e máximo.

**Como usar**
- Execute a partir da raiz do projeto:
  ```bash
  python scripts/simulador_realtime.py --interval-min 1 --interval-max 3 --cycles 100
  ```

**Argumentos úteis**
- `--interval-min`: intervalo mínimo em segundos entre ciclos (default: `1.0`)
- `--interval-max`: intervalo máximo em segundos entre ciclos (default: `3.0`)
- `--cycles`: número máximo de ciclos; `0` = executa continuamente
- `--seed`: semente para gerar valores determinísticos
- `--sensor`: IDs de sensores específicos para simular
- `--equipamento`: IDs de equipamentos específicos para simular
- `--dry-run`: não grava leituras no banco, apenas emula o fluxo
- `--debug`: habilita logs de depuração

## 3. `stress_telemetry.py`

**O que faz**
- Testa a capacidade do sistema de processar muitas leituras de telemetria rapidamente.
- Cria um cenário controlado com um equipamento e um sensor de stress.
- Insere leituras concorrentes em múltiplas threads.
- Avalia se alertas e ordens de serviço são gerados corretamente a partir das leituras.

**Como usar**
- Execute a partir da raiz do projeto:
  ```bash
  python scripts/stress_telemetry.py --leituras 1000 --threads 20
  ```

**Argumentos disponíveis**
- `--leituras`: total de leituras a inserir (default: `100`)
- `--threads`: número de threads concorrentes para inserir leituras (default: `5`)

## Dicas gerais

- Use `python -m py_compile scripts/<script>.py` para verificar sintaxe antes de rodar.
- Se quiser testes mais avançados, os scripts podem ser expandidos com parâmetros adicionais para:
  - variabilidade nos perfis de sensores
  - intensidade e classificação de alertas
  - diferentes cenários de falha por equipamento
  - modo de execução em lote vs. tempo real
