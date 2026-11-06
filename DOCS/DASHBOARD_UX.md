# Dashboard e acompanhamento de medições

## Página inicial por perfil

- **Administrador sem empresa selecionada:** comparação de todas as empresas, inclusive sem equipamentos. Ordenação por alertas críticos ativos, ordens abertas sem responsável e nome. A busca é local sobre o resumo completo. “Ver empresa” aplica o contexto global; “Voltar às empresas” o remove.
- **Gestor e administrador com empresa selecionada:** prioridades operacionais; filtros de setor e equipamento afetam contagens, filas e desempenho. São mostradas cinco ordens abertas e cinco alertas ativos. A fila ordena ordens por prioridade/antiguidade e alertas por gravidade/data mais recente. Alertas antigos ainda ativos permanecem relevantes.
- **Técnico:** minhas pendentes, meus atendimentos e disponíveis para assumir. A fila pessoal põe atendimentos em andamento primeiro. Equipamentos do acompanhamento correspondem às ordens próprias ou sem responsável da empresa; ordens encerradas não entram nas contagens de trabalho aberto.

O resumo é atualizado a cada 30 segundos enquanto a página está visível. Custos e indicadores são consultados somente quando a seção de desempenho está expandida. Uma falha preserva o resumo anterior, com mensagem e horário da última atualização. Os atalhos de ordens enviam filtros ao servidor, inclusive na paginação.

MTTR é calculado sobre ordens concluídas; MTBF usa intervalos positivos entre intervenções concluídas. Disponibilidade é uma estimativa desses registros, não uma medição de uptime. A nova apresentação usa `null` quando falta histórico; custo zero e duração zero continuam sendo valores válidos.

## Gráfico ao vivo

O componente compartilhado em `FrontATT/live-chart.js` tem instâncias independentes no dashboard e na Telemetria. Painéis recolhidos não instanciam o componente e não consultam leituras.

- O usuário escolhe equipamento e sensor. A escolha automática ocorre apenas com uma opção disponível.
- Uma consulta é iniciada a cada **5 segundos**; chamadas em andamento não se sobrepõem. Essa frequência não modifica a ingestão dos sensores.
- O padrão é **Automático — últimas 60 leituras**. Os pontos são ordenados por timestamp registrado e ID; o eixo horizontal usa tempo real, sem espaçamento artificialmente uniforme.
- Também há janelas de 5/15 minutos, 1/6/24 horas, terminando na última medição disponível. O gráfico não avança com o relógio quando não existem novidades. O horário final fica explícito.
- Sensor a cada 2 s: geralmente acrescenta 2–3 pontos por consulta. Sensor a cada 10 s: as consultas intermediárias preservam o desenho. Sensor a cada 10 min: o histórico automático continua visível, sem diagnosticar falha pela ausência de novidades.
- Valores iguais em timestamps novos são novas medições e formam trechos horizontais reais. Não há prolongamento artificial do último valor até o presente.
- Uma única leitura é um marcador. A ausência de leituras tem estado próprio. Leituras inválidas são descartadas e IDs repetidos são deduplicados.
- Janelas fixas têm teto de 1.000 leituras recentes, com aviso explícito de truncamento. A paginação usa timestamp final e ID máximo para estabilizar a amostra enquanto chegam dados.
- Limites operacionais usam os percentuais do sensor, com padrões 70/85/100 somente para campos nulos. Limites inválidos não são desenhados. Cada nível tem rótulo e tracejado próprios; a escala inclui valores e limites com margem de 8%.
- A escala expande para acomodar novidades. “Ajustar escala”, troca de sensor ou de janela permitem reduzi-la. Alterações animam por cerca de 300 ms, respeitando movimento reduzido; respostas idênticas não animam.
- “Última consulta” descreve a comunicação com o servidor. “Última medição” e sua idade descrevem os dados. O cadastro não informa frequência esperada: espera por dados não equivale a sensor offline.
- Pausa, página oculta, painel fechado, navegação e logout encerram consultas/animações. Respostas de contextos antigos são descartadas. Retomar busca o estado atual.

Gráficos de tendências exibem a **amostra analisada**, com eixo temporal, unidade e limite superior da análise. Não são identificados como uma transmissão de medições ao vivo. As regras de detecção, alertas e ordens não foram alteradas.

## Contratos adicionados

`GET /api/dashboards/resumo/` mantém os campos legados e aceita:

| Parâmetro | Comportamento |
|---|---|
| `incluir_desempenho` | Booleano; padrão `true` por compatibilidade. `false` omite cálculos por equipamento, KPIs e custos. |
| `setor` | Recorte operacional exato pelo setor do equipamento. |
| `equipamento_id` | Recorte por equipamento dentro do escopo permitido. |
| `empresa_id` | Contexto de empresa para administrador; não amplia o escopo dos demais perfis. |
| `dias` | Inteiro positivo; mantém o recorte legado pela abertura das ordens concluídas. |

Novos campos: `atualizado_em`, `opcoes_equipamentos`, `setores`, `ordens_prioritarias`, `alertas_prioritarios`, `ordens_sem_tecnico`; para técnicos, contagens pessoais e filas próprias/disponíveis; para administrador consolidado, `empresas`, `total_empresas`, `empresas_com_alertas_criticos`. Quando solicitado, `desempenho` contém métricas com suficiência explícita e `custos_por_dia` agrega registros por data de execução.

Ordens aceitam `abertas=true`, `responsavel_escopo=minhas|livres` e `setor`. Alertas aceitam `setor` e o filtro existente de status. Sensores e leituras aceitam `escopo_operacional=true` para restringir o acompanhamento do técnico ao mesmo escopo de equipamentos da página inicial. Leituras também aceitam `id_ate` para paginação de uma amostra estável. Nenhum filtro amplia as permissões da empresa.

Não há migração de banco ou comunicação por WebSocket. Para validar:

```powershell
node --test FrontATT/live-chart.test.cjs FrontATT/telemetria.test.cjs
python manage.py test manutencao.dashboards --settings=app.test_settings --noinput
```

## Leituras, linha de tendência e horário estimado

Na página **Tendências**, a linha azul e os pontos são as leituras registradas. A linha roxa tracejada é a regressão calculada pelo servidor sobre **a mesma amostra**, limitada aos seus horários inicial e final. Ela aparece quando a análise está ativa e a amostra tem quantidade e duração suficientes. Uma reta ajustada não confirma, sozinha, uma anomalia; os critérios existentes de ritmo, persistência, R² e direção permanecem válidos.

No acompanhamento ao vivo do dashboard e da Telemetria, **Mostrar tendência e projeção** é opcional. A regressão visual usa somente as leituras exibidas, com no mínimo três horários distintos, sem chamadas adicionais à API. Essa reta não altera a detecção de alertas nem representa os critérios da análise oficial. Sem novas medições, as duas linhas permanecem paradas.

A API de tendências passa a fornecer `regression_line` (dois pontos com timestamp e valor ajustado, sem arredondar os coeficientes para desenhar) e `projected_breach_at` (data/hora calculada com o último valor observado e o ritmo da regressão). Ambos são nulos quando não existe base para seu cálculo. O novo horário é ancorado na **última medição**, nunca no horário da consulta, preservando as regras anteriores de projeção em horas/minutos.

**Ver estimativa de horário até o limite** fica recolhido junto ao gráfico da amostra. Só aparece para uma projeção crescente válida cujo horário ainda esteja no futuro em relação à análise. Exibe horário aproximado, duração e a medição de referência; não desenha medições futuras nem anuncia horário de falha. Projeções inexistentes, no passado, de séries decrescentes/estáveis ou de amostras insuficientes não exibem esse detalhe. As datas são apresentadas no horário local.


## Trecho à frente da última leitura

A continuação roxa é desenhada em área sombreada, após uma divisão na última medição real. O histórico ajustado usa traços longos; o trecho estimado usa traços curtos e termina em marcador vazado. A curva e os pontos azuis continuam exclusivamente no período observado.

A escala de tempo permanece uniforme: a projeção acrescenta no máximo metade da duração observada e tem teto de 24 horas. Assim, pelo menos dois terços da área temporal permanecem dedicados ao histórico. Esse teto é apenas de apresentação, não de detecção: uma estimativa de alcance do limite mais distante continua disponível no detalhe de horário, sem comprimir o histórico para desenhar toda a extrapolação.

Se o limite superior for alcançado dentro do trecho mostrado, a curva projetada termina no limite e o marcador identifica o alcance estimado. Se estiver além, a legenda informa que o limite não é atingido no trecho visível. Uma projeção de queda nunca inventa alcance do limite superior.

Na análise oficial, a continuação exige análise ativa, amostra suficiente e direção crescente ou decrescente validada pelos critérios existentes. No acompanhamento visual da janela, exige ao menos três horários distintos, ajuste R² mínimo de 0,8, persistência mínima de 0,7 e ritmo diferente de zero; isso não dispara alertas nem substitui os critérios oficiais. Amostras estáveis, ruidosas ou insuficientes não ganham trecho futuro.

A continuação parte do último **valor medido** e usa o ritmo da reta ajustada, seguindo a mesma referência da estimativa de horário do servidor. O trecho roxo continua ancorado nessa medição quando não chegam dados. Os horários do eixo incluem a extensão estimada, enquanto o rodapé identifica separadamente a última leitura real e o fim da projeção. Não houve alteração na API, no processamento de alertas ou no banco para esta extensão visual.
