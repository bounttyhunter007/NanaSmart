# Scripts na pasta `scripts`

Este documento descreve brevemente os scripts disponíveis em `scripts/` e como usá-los.

## 1. `seed_db.py`

Substitui a base por dados sintéticos com nomes operacionais, com cadastros compatíveis,
cronologia validada, histórico recente para KPIs e cenários previsíveis.
O [roteiro completo](../DOCS/APRESENTACAO_DADOS.md) explica as contas e os três perfis.

```powershell
# Consulta parâmetros e migrações; não altera a base
python scripts/seed_db.py --check

# Geração destrutiva, atômica e reproduzível
python scripts/seed_db.py --empresas 2 --equipamentos 10 --funcionarios 4 --days 120 --seed 42

# Limpeza sem repopulação
python scripts/seed_db.py --clean-only
```

- Padrões: duas empresas, dez equipamentos por empresa, quatro funcionários
  (um gestor e três técnicos), 120 dias e semente 42.
- Empresas, equipamentos e dias devem ser positivos; funcionários têm mínimo dois.
  Com menos de três equipamentos/empresa, avisa que a cobertura é parcial.
- Cada empresa recebe equipamentos A/B/C, trabalho pendente e em andamento para
  cada técnico, ordens livres e conclusões recentes com custos. Com cinco ativos,
  também há equipamento em manutenção e inativo.
- Os três primeiros equipamentos são motor estável, bomba com tendência de
  temperatura e compressor de reserva com pressão crítica, vibração recuperada
  e recorrência de temperatura. Os episódios seguem os serviços reais.
- Leituras estáveis/antigas têm intervalos de 40 a 85 minutos; os cenários das
  últimas 24 horas usam 10 a 20 minutos. A leitura final dos cenários fica cinco
  minutos antes da geração. Inativos têm sensores desativados e leituras antigas.
- A limpeza e a geração são uma transação: falhas revertem ambas. Superusuários e
  perfis `admin` preservam credenciais e perdem o vínculo com empresas removidas.
  Superusuários recebem o perfil `admin` utilizado nas permissões da aplicação.
- O resumo após o commit imprime logins reais, IDs, perfis dos sensores, próximo
  disparo por horímetro e comandos para movimentar apenas o motor escolhido.
  Gestores e técnicos usam logins `nome.sobrenome` e senha `123`; consulte o
  resumo para cada empresa. Colisões com contas preservadas recebem sufixo numérico. `admin` novo usa `admin`; senhas existentes não mudam.
- `--seed` repete dados e valores, mas datas são relativas à execução e IDs podem
  mudar. As configurações globais continuam com duas horas mínimas para tendência.
- Saída: `0` sucesso, `1` falha, `2` parâmetros inválidos, `130` interrupção.

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
- `--check`: confere banco, filtros e limites e encerra sem simular; falha se não houver sensor elegível ou se houver limites inválidos.
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
reduz o padrão de duas horas nem garante uma OS após alguns ciclos. Para uma
apresentação curta, use o teste guiado da página Tendências ou configure
explicitamente o sensor de teste. O simulador não muda essa configuração.

As gravações passam por `Telemetria.save()` e pelos sinais reais: podem criar
alertas, análises preditivas e ordens de serviço conforme as regras atuais.
Não usa `bulk_create` nem cria alertas manualmente. O valor, alvo, ruído e estado
do episódio só avançam após uma
gravação bem-sucedida; uma falha de banco por sensor não desfaz os outros sensores.
Sensores e limites são atualizados a cada ciclo, e o histórico é consultado somente
para sensores que entram na simulação. Execuções simultâneas no mesmo sensor
podem intercalar leituras; prefira filtros sem sobreposição.

Saída: `0` ao terminar sem falhas e com leituras gravadas/simuladas, `1` por erro, seleção vazia em execução finita ou limite de falhas,
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
