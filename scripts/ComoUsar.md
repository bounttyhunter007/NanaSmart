# Scripts na pasta `scripts`

Este documento descreve brevemente os scripts disponíveis em `scripts/` e como usá-los.

## 1. `seed_db.py`

**O que faz**
- Popula o banco de dados com dados falsos industriais realistas.
- Cria empresas, gestores, técnicos, equipamentos, sensores, planos de manutenção, telemetria, ordens de serviço e alertas.
- Gera histórico de telemetria e cronogramas de manutenção mais coesos para MTTR/MTBF.

**Como ficam as leituras**
- Os intervalos variam aleatoriamente entre **40 e 85 minutos**, mantendo os horários reais no banco. A última leitura fica entre 2 e 12 minutos antes do instante de referência do seed.
- Em cada grupo de cinco sensores, três têm operação estável, um tem aumento gradual e um tem recuperação; a ordem dos perfis é embaralhada.
- Há pequenas oscilações suaves e ruído proporcional ao limite de cada sensor. Sensores de vibração ou pressão não recebem o mesmo ruído absoluto de uma temperatura.
- Nos perfis de aumento e recuperação, a mudança aparece nas últimas 24 horas. O histórico antigo não acumula desgaste durante meses até ficar preso em um teto.
- Os dados de exemplo passam pelos serviços reais de tendência e limite após a importação. O seed não acrescenta mais picos de 110% seguidos de quedas a 30% apenas para gerar alertas. As regras operacionais continuam decidindo quais alertas e ordens criar.
- A projeção continua sendo uma reta: horários irregulares e valores mais variados tornam o histórico e a inclinação mais fáceis de comparar; não alteram o modelo linear do gráfico.

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

# Oscilações suaves para acompanhar o gráfico, usando um sensor existente
python scripts/simulador_realtime.py --sensor 1 --cenario oscilacao --seed 42

# Aumento persistente: ritmo médio de 15% do limite por hora
python scripts/simulador_realtime.py --sensor 1 --cenario tendencia --seed 42

# Demonstração de limites: 5 fases de 60 ciclos cada, com transições graduais
python scripts/simulador_realtime.py --sensor 1 --cenario escalada --fase-ciclos 60 --cycles 300 --seed 42

# Leituras um pouco mais espaçadas, com variação ainda menor por coleta
python scripts/simulador_realtime.py --sensor 1 --interval-min 5 --interval-max 12 --variacao-max-pct 0.5
```

- `--interval-min` / `--interval-max`: cadência aleatória de **3 a 7 segundos** por padrão.
  O tempo de processamento é descontado da espera; não há espera após o último ciclo.
- `--cycles`: ciclos a executar; `0` mantém execução contínua. Ctrl+C encerra.
- `--empresa`, `--equipamento`, `--sensor`: aceitam vários IDs separados por espaços;
  filtros combinados usam interseção. IDs inexistentes/inativos não geram dados.
- `--cenario`: `normal`, `misto` (padrão), `baixo`, `medio`, `critico`,
  `recuperacao`, `escalada`, `tendencia` ou `oscilacao`.
- `--fase-ciclos`: duração de cada fase da escalada (padrão **60 ciclos**). Repete
  normal → baixo → médio → crítico → recuperação.
- `--variacao-max-pct`: mudança máxima entre duas leituras, em percentual do limite do sensor (padrão **1%**, maior que zero e até 5%). Um limite de 100 permite variar até 1 unidade por leitura; um limite de 7 permite até 0,07.
- `--chance-anomalia`: probabilidade de iniciar um episódio por sensor/ciclo no modo misto (padrão **0.002**, ou 0,2%). O episódio dura de 60 a 120 ciclos adicionais, com aproximação gradual da faixa. Níveis baixos são mais frequentes que médios e críticos; não há um sorteio independente de pico em cada leitura.
- `--seed`: sequência reproduzível para o mesmo cadastro, histórico inicial e cenário.
- `--max-falhas`: encerra após ciclos consecutivos com falha (padrão 5).
- `--dry-run`: consulta o banco e atualiza memória local, sem leituras ou efeitos persistidos.
- `--debug`: detalhes por sensor; normalmente exibe somente resumo por ciclo.

Os cenários usam os três percentuais configurados em cada sensor (padrões
70/85/100), inclusive quando o crítico está abaixo de 100%. Não impõem um limite
fictício de 100 para configurações inválidas: identificam e ignoram o sensor.
No modo normal, cada sensor mantém um alvo por 18 a 36 ciclos, com ruído suave
proporcional à sua escala. Temperatura e umidade respondem mais lentamente que
corrente e vibração. O modo `oscilacao` usa um alvo que sobe e desce gradualmente,
mantendo a faixa normal como referência. Cada sensor tem seu próprio estado.

Os cenários de alerta e recuperação definem **faixas-alvo**, sem obrigar o valor
a saltar imediatamente para elas. Uma leitura inicial alta demora a baixar;
uma inicial normal demora a alcançar o crítico. Fases muito curtas podem terminar
antes de alcançar o alvo. O alerta só aparece ao cruzar a faixa com uma leitura
real; a recuperação exige duas leituras abaixo do limiar baixo.
Se o limiar baixo for zero, não existe faixa não negativa de recuperação.

O cenário `tendencia` gera subida persistente, com ritmo médio de **15% do limite
por hora** e pequenas variações no ritmo, até o teto de crítico + 15% do limite.
Esse avanço acompanha o tempo entre ciclos, evitando acelerar a subida apenas
porque a coleta ficou mais frequente. Após pausas longas, a retomada considera
no máximo 60 segundos de avanço, respeitando também o limite por leitura.
Valores já acima desse teto não são reduzidos artificialmente nesse cenário.

Os horários continuam sendo os instantes reais de gravação. As regras preditivas
de quantidade, duração, R² e persistência continuam valendo: o simulador não
reduz o padrão de 30 minutos nem garante uma OS após alguns ciclos. Para uma
apresentação curta, use o teste guiado [DEMO] da página Tendências ou configure
explicitamente o sensor de teste. O simulador não muda essa configuração.

As gravações passam por `Telemetria.save()` e pelos sinais reais: podem criar
alertas, análises preditivas e ordens de serviço conforme as regras atuais.
Não usa `bulk_create` nem cria alertas manualmente. O valor, alvo, ruído e estado
do episódio só avançam após uma
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
