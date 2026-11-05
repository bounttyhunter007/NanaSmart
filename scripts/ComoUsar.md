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

Gera leituras para sensores ativos de equipamentos em operação. Usa os modelos e
as configurações Django atuais (`DJANGO_SETTINGS_MODULE`, padrão `app.settings`).
Verifica migrações antes de iniciar; não cria tabelas nem cadastros.

```bash
# Conferir sem gravar; --debug mostra cada leitura
python scripts/simulador_realtime.py --dry-run --cycles 3 --debug

# Operação contínua, restrita à empresa escolhida
python scripts/simulador_realtime.py --empresa 1 --cenario normal

# Demonstração completa: 5 fases de 8 ciclos cada
python scripts/simulador_realtime.py --sensor 1 --cenario escalada --cycles 40 --seed 42
```

- `--interval-min` / `--interval-max`: cadência de 1 a 3 segundos por padrão.
  O tempo de processamento é descontado da espera; não há espera após o último ciclo.
- `--cycles`: ciclos a executar; `0` mantém execução contínua. Ctrl+C encerra.
- `--empresa`, `--equipamento`, `--sensor`: aceitam vários IDs separados por espaços;
  filtros combinados usam interseção. IDs inexistentes/inativos não geram dados.
- `--cenario`: `normal`, `misto` (padrão), `baixo`, `medio`, `critico`,
  `recuperacao` ou `escalada`.
- `--fase-ciclos`: duração de cada fase da escalada (padrão 8). Repete
  normal → baixo → médio → crítico → recuperação.
- `--chance-anomalia`: probabilidade por sensor/ciclo no modo misto (padrão 0.01).
- `--seed`: sequência reproduzível para o mesmo cadastro, histórico inicial e cenário.
- `--max-falhas`: encerra após ciclos consecutivos com falha (padrão 5).
- `--dry-run`: consulta o banco e atualiza memória local, sem leituras ou efeitos persistidos.
- `--debug`: detalhes por sensor; normalmente exibe somente resumo por ciclo.

Os cenários usam os três percentuais configurados em cada sensor (padrões
70/85/100), inclusive quando o crítico está abaixo de 100%. Não impõem um limite
fictício de 100 para configurações inválidas: identificam e ignoram o sensor.
No modo normal há variação suave dentro da faixa segura; cenários de alerta
entram diretamente na faixa escolhida. Recuperação produz leituras abaixo do
limiar baixo (a aplicação exige duas leituras normais para resolver uma ocorrência).
Se o limiar baixo for zero, não existe faixa não negativa de recuperação.

As gravações passam por `Telemetria.save()` e pelos sinais reais: podem criar
alertas, análises preditivas e ordens de serviço conforme as regras atuais.
Não usa `bulk_create` nem cria alertas manualmente. A memória só avança após uma
gravação bem-sucedida; uma falha de banco por sensor não desfaz os outros sensores.
Sensores e limites são atualizados a cada ciclo, e o histórico é consultado somente
para sensores que entram na simulação. Execuções simultâneas no mesmo sensor
podem intercalar leituras; prefira filtros sem sobreposição.

Saída: `0` ao terminar sem falha no último ciclo, `1` por erro ou limite de falhas,
`130` por interrupção do operador; argumentos inválidos retornam `2`.

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
