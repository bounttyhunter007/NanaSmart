# Identificação de tendências e geração antecipada de OS

Data: 06/11/2026. Documento vigente do requisito 1; substitui as regras anteriores de `docs_padroes_projeto/1-ANALISE_TENDENCIAS_PREDITIVAS.md`.

## Requisito definido

Com a análise ativa e uma amostra suficiente, identificar aumentos ou reduções persistentes considerados anormais para o sensor. Registrar um alerta com equipamento, sensor, direção, leituras e critérios utilizados. Abrir uma OS preditiva de inspeção para a condição confirmada, antes de exigir ultrapassagem do limite operacional.

A projeção indica tempo estimado até o limite superior se a inclinação continuar. Não representa prazo de quebra. Uma redução só é anormal quando configurada como tal: por exemplo, resfriamento pode ser recuperação em um equipamento e perda de processo em outro.

## Diagnóstico do código anterior

| Parte existente | Problema encontrado | Decisão implementada |
|---|---|---|
| Regressão por tempo real e seleção das últimas leituras | Inclinação sozinha aceitava oscilações ou picos como tendência; rajadas podiam produzir inclinações enormes | Exigir duração, R² e fração de intervalos no mesmo sentido |
| `num_leituras` | Era o máximo, mas a suficiência era fixada em três | Manter o máximo e adicionar `minimo_leituras` independente |
| Configuração com `ativo=false` | Era ignorada, fazendo a rotina usar global ou defaults ativos | A configuração efetiva vale inclusive quando desativada |
| Tendências decrescentes | Apareciam na consulta, mas nunca geravam alerta | Configurar os sentidos anormais por sensor ou globalmente |
| Amostragem | Limite intermediário de registros podia deixar duplicatas consumirem toda a cota; datas futuras não eram excluídas | Percorrer registros até obter a cota válida, com janela fechada em agora |
| Alertas e OS | Só aumentos com risco suficiente alertavam; OS exigia alto risco ou projeção de até 24h | Toda anomalia confirmada gera alerta e uma OS preditiva de inspeção |
| Concorrência | Análise ocorria antes do bloqueio e não serializava com a ingestão | Bloquear sensor antes de analisar; manter bloqueio até concluir os efeitos |
| Formulário | Sempre salvava ativo; usava defaults locais ao herdar global | Permitir desativar e carregar os valores efetivos do backend |

Foram preservados: execução por sinal de nova leitura, comando periódico, separação por empresa, registro dos episódios, vínculos de OS e independência do Gemini. O monitoramento por limites continua separado da tendência.

## Configuração e precedência

Prioridade: configuração específica do sensor, depois configuração global mais recente por id, depois defaults do modelo. Uma específica ativa pode sobrepor uma global inativa; uma específica inativa bloqueia a análise daquele sensor. O banco legado permite várias configurações globais; a escolha pela mais recente é explícita e determinística, sem excluir dados existentes. Para mudar a global em uso, editar a de maior id.

| Campo | Default | Regra |
|---|---:|---|
| `ativo` | `true` | Habilita a análise efetiva |
| `periodo_horas` | 24 | Inteiro >= 1; janela retrospectiva |
| `num_leituras` | 50 | Máximo de amostras válidas, de 3 a 500 |
| `minimo_leituras` | 3 | Mínimo de horários distintos, de 3 até `num_leituras` |
| `duracao_minima_minutos` | 30 | Inteiro >= 1, no máximo a janela; distância entre primeira e última leitura |
| `sensibilidade` | `media` | Alta, média ou baixa: limiar de inclinação descrito abaixo |
| `persistencia_minima` | 0,70 | Fração dos intervalos que seguem estritamente o sentido da inclinação; de 0,5 a 1 |
| `r2_minimo` | 0,80 | Qualidade mínima do ajuste linear; de 0,5 a 1 |
| `direcao_alerta` | `crescente` | `crescente`, `decrescente` ou `ambas` |

O sentido padrão preserva a interpretação anterior dos sensores com limite superior. Os novos critérios são defaults técnicos iniciais, ajustáveis pelo responsável pela manutenção. A frequência de coleta e o máximo de leituras devem permitir cobrir a duração mínima: 50 leituras a cada segundo não cobrem 30 minutos e, portanto, não produzem uma análise suficiente. Nesse caso, ajustar a duração ou a frequência de coleta. A rotina não faz reamostragem automática.

Modelo, administração e API validam as combinações de critérios, incluindo alterações parciais com os valores já existentes. `bulk_create`/`update` de configurações dispensam a validação do Django; importações devem validar os dados antes de usá-los.

## Algoritmo verificável

1. Capturar um único instante `agora`; não analisar sensor inativo ou inexistente.
2. Se a configuração efetiva está desativada, retornar `analysis_enabled=false`, `data_quality=disabled`, sem novos efeitos operacionais.
3. Selecionar registros em `[agora - periodo_horas, agora]`, por timestamp decrescente e id decrescente. Descartar valores não finitos. Por timestamp, manter o registro válido de maior id. Parar ao atingir `num_leituras`; ordenar a amostra cronologicamente.
4. Exigir pelo menos `minimo_leituras` horários distintos e duração >= `duracao_minima_minutos`. Caso contrário, retornar `insufficient_data=true`, sem projeção ou novo alerta.
5. Ajustar `valor = intercepto + inclinação × horas`, usando horas desde a primeira leitura. O cálculo usa somas centradas para reduzir cancelamento numérico.
6. Comparar inclinação com o limiar absoluto: `fator × abs(limite_alerta)`. Fatores: alta = 0,005; média = 0,02; baixa = 0,05. Se o limite for zero, usar o fator em unidade/hora. Crescente exige inclinação estritamente maior que o limiar; decrescente exige inclinação estritamente menor que o negativo do limiar.
7. Calcular `R² = 1 - soma(resíduos²) / soma((valor - média)²)`, limitado ao intervalo [0, 1]. Série constante tem R² = 1, mas inclinação zero e permanece estável.
8. Calcular persistência como quantidade de diferenças consecutivas no sentido da inclinação dividida por `n - 1`. Intervalos sem alteração e intervalos no sentido contrário contam contra a persistência.
9. Confirmar direção somente com R² e persistência >= seus mínimos. Caso contrário, classificar como `stable`, mantendo os indicadores para auditoria.
10. `is_anomalous=true` somente se a direção confirmada pertence a `direcao_alerta`. Recomendar inspeção e gerar OS para toda anomalia confirmada.

Exemplo: limite 100, sensibilidade média, valores 10, 20 e 30 em intervalos de 30 minutos. Inclinação = 20 unidades/h, limiar = 2, R² = 1, persistência = 100%, duração = 60 minutos. Com aumento configurado como anormal, gera alerta e OS mesmo abaixo do primeiro alerta por limite. A mesma amostra concentrada em dois minutos é insuficiente com os defaults.

Para queda 60, 50, 40 nos mesmos intervalos, a direção é decrescente. Com default crescente, não é anomalia operacional; com `decrescente` ou `ambas`, gera alerta e OS, sem projeção de limite inferior.

## Projeção e risco

Somente tendência crescente confirmada projeta o limite superior: `max(0, (limite - último_valor) / inclinação)`, em horas. Não há projeção para séries estáveis ou quedas. A projeção usa o último valor observado e a inclinação ajustada. O cadastro atual não possui limite inferior.

A classificação mantém as faixas preexistentes de risco: crítico se já atingiu o limite ou a projeção é <= 2 horas; alto para projeção <= 8 horas; médio para <= 24 horas. Fora dessas condições, para limites positivos, valor >= 85% resulta em alto e >= 70% em médio. Toda anomalia confirmada tem pelo menos risco médio. O risco influencia a prioridade da OS pela matriz existente de criticidade e gravidade; ele não é requisito adicional para abrir a inspeção.

O modelo de alerta possui níveis `baixo`, `medio`, `critico`: riscos alto e crítico são representados como alerta crítico, preservando esse mapeamento existente. A OS recebe a gravidade específica do risco original. Valores acima do limite podem continuar sendo críticos mesmo quando a tendência é decrescente; os alertas por limite são independentes.

## Episódios e ordens de serviço

- Chave do episódio: `tendencia:<sensor_id>:<increasing|decreasing>`.
- Ao confirmar anomalia, criar ou atualizar o alerta ativo, com `origem=tendencia`, sensor, equipamento e `dados_analise` contendo amostra e critérios. O sinal de alerta cria a OS `preditiva`, vinculada por `alerta_origem`, `sensor_origem` e `ordem_servico`.
- Reexecutar na mesma condição atualiza o episódio e a mesma OS. Uma OS concluída ou cancelada não é recriada enquanto esse episódio permanece ativo. Prioridade manual permanece preservada.
- Com amostra suficiente e ausência da condição anormal, resolver o alerta ativo. Isso inclui estabilização, reversão ou mudança para um sentido não configurado. A resolução não encerra a OS.
- Mudança para outro sentido anormal resolve o episódio anterior e abre outro. Após recuperação, recorrência também pode abrir novo episódio e nova OS; uma OS anterior ainda aberta permanece sob gestão humana.
- Desativação, dados insuficientes e expiração dos dados não provam recuperação: não resolvem automaticamente alertas anteriores e não encerram OS. Ao reativar, a próxima leitura ou execução periódica retoma a avaliação.
- Bloqueio de linha do sensor envolve a análise e os efeitos, na mesma ordem usada pela ingestão. A restrição parcial de unicidade de alerta e a relação única de origem da OS permanecem como proteção adicional.

O Gemini pode explicar os dados, mas não decide a criação do alerta nem da OS.

## API e interface

Configurações: CRUD `/api/telemetria/trend-config/`, incluindo filtro `?sensor=<id>`. Administrador pode gerenciar a global; gestores ficam limitados a sensores de sua empresa; técnicos continuam sujeitos às permissões existentes.

Exemplo de criação específica:

```json
{
  "sensor": 1,
  "ativo": true,
  "periodo_horas": 24,
  "num_leituras": 50,
  "minimo_leituras": 10,
  "duracao_minima_minutos": 60,
  "sensibilidade": "media",
  "persistencia_minima": 0.7,
  "r2_minimo": 0.8,
  "direcao_alerta": "ambas"
}
```

Consulta: `GET /api/telemetria/tendencias/?sensor_id=1`, sem gravações. A resposta mantém os campos anteriores e adiciona `analysis_enabled`, `is_anomalous`, `sample_duration_minutes`, `r_squared`, `persistence_ratio` e origem da configuração (`config_used.source`: `sensor`, `global`, `padrao`). `readings_summary` tem timestamps ISO tanto em amostras suficientes quanto insuficientes. `active_alert_id` e `predictive_work_order` mostram os vínculos atuais. O GET não sincroniza alertas/ordens; os efeitos acontecem na ingestão ou pelo comando periódico.

A lista padrão omite análises desativadas e insuficientes. `?all=true` inclui esses estados; a consulta individual também os retorna. Ela pode mostrar tendências em sentidos não configurados e risco por proximidade do limite: `is_anomalous` é o indicador que decide o fluxo preditivo.

No frontend, o botão de configuração no detalhe do sensor permite editar todos os critérios e habilitar/desabilitar. Quando não há específica, o formulário carrega a configuração efetiva do backend. O detalhe distingue análise desativada de dados ainda insuficientes.

## Execução e migração

Cada nova `Telemetria` criada por `save()` dispara o fluxo na mesma transação. `bulk_create`, importações e alterações por `update()` não disparam sinais: executar o comando após essas operações quando desejar sincronização.

```powershell
python manage.py migrate
python manage.py analisar_tendencias
```

Migração versionada: `telemetria/0002_trendconfig_direcao_alerta_and_more.py`. Acrescenta cinco campos com defaults, mantendo a janela, máximo, sensibilidade, sensor e ativação existentes. Não exclui dados nem reclassifica episódios históricos. A regra nova pode abrir inspeções onde antes havia apenas alerta ou tendência distante do limite; reavaliar os critérios operacionais antes de executar a rotina em produção.

Agendar `analisar_tendencias` pelo mecanismo do ambiente quando for necessário revisar períodos sem novas leituras. O repositório entrega o comando, sem instalar um agendamento no sistema operacional.

## Critérios de aceitação e cobertura

| Cenário | Resultado esperado |
|---|---|
| Análise ativa, mínimo/duração atendidos, inclinação/R²/persistência atendidos, sentido configurado | Alerta com equipamento, sensor e condição; uma OS preditiva |
| Menos leituras que o mínimo, mesmo com inclinação forte | Insuficiente, sem novo alerta/OS |
| Muitas leituras em poucos segundos | Insuficiente se não cobrir a duração mínima |
| Pico isolado, oscilação ou persistência abaixo do configurado | Sem anomalia confirmada |
| Queda com configuração crescente | Direção informada, sem alerta de tendência |
| Queda com configuração decrescente ou ambas | Alerta e OS de inspeção, sem projeção inferior |
| Específica inativa e global ativa | Análise desativada; sem fallback |
| Global inativa, sem específica | Análise desativada; sem fallback |
| Datas futuras, antigas ou valores infinitos | Excluídos da amostra |
| Várias leituras no mesmo horário | Uma amostra válida por horário; duplicatas não esgotam a cota |
| Repetição, execução periódica e concorrência | Um alerta ativo e uma OS por episódio |
| Estabilização comprovada | Alerta resolvido, OS preservada |
| Desativação ou dados expirados após alerta | Alerta preservado; ausência de evidência não confirma recuperação |
| Consulta de tendência por GET | Nenhuma criação de alerta/OS |
| Critérios inválidos ou PATCH incompatível | Validação rejeita a alteração |

Testes: `telemetria/test_trend_analysis.py`, `telemetria/test_alert_concurrency.py` e a suíte existente de API, alertas, manutenção, simulação e migrações.

```powershell
python manage.py test --settings=app.test_settings --noinput
python manage.py makemigrations --check --dry-run --settings=app.test_settings
node --check FrontATT/app.js
```

Validação realizada em 06/11/2026:

- PostgreSQL 18: **109 testes aprovados**, sem skips, incluindo três casos de concorrência (ingestão, processamento de alerta e análise de tendência simultâneos).
- SQLite descartável: **106 testes aprovados, três skips esperados**, pois não suporta o bloqueio de linha exigido nos testes concorrentes.
- `makemigrations --check --dry-run`: nenhuma divergência entre modelos e migrações.
- `node --check FrontATT/app.js`: sintaxe válida. O formulário não foi validado visualmente em navegador nesta entrega.
- `git diff --check`: sem erros de whitespace.

O PostgreSQL foi iniciado em cluster descartável local `.venv/nanasmart-trend-pg-tests`, porta 55440, com `NANASMART_TEST_POSTGRES_PORT=55440`, e encerrado após a suíte. O banco de desenvolvimento não foi acessado nem migrado; executar `python manage.py migrate` no ambiente de destino antes de iniciar a versão nova.

Durante a validação completa no PostgreSQL, os testes preexistentes do simulador revelaram um problema de isolamento: o processo fecha as conexões, mas `TestCase` mantinha uma transação externa nelas. `telemetria/test_simulador_realtime.py` passou a usar `TransactionTestCase`, compatível com esse comportamento. O código do simulador não foi alterado.

Arquivos centrais: `telemetria/models.py`, `serializers.py`, `trend_analysis.py`, `predictive_service.py`, `admin.py`, a migração `0002`, os testes de tendência/concorrência/simulador e `FrontATT/app.js`/`index.html`. README, referência de API e documentação anterior receberam links para esta especificação.
