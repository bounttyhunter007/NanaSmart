# Demonstração de tendências: gráfico, alerta e OS

Revisão: 06/11/2026. Roteiro de apresentação e descrição da implementação. Complementa [Identificação de tendências](IDENTIFICACAO_TENDENCIAS.md) e [Telemetria e UX](TELEMETRIA_UX.md).

## O que dizer ao apresentar

> Uma leitura informa o valor atual. A tendência mede a direção e o ritmo de mudança ao longo do tempo. O sistema verifica se há leituras suficientes, tempo de observação, repetição e consistência antes de recomendar uma inspeção.
>
> A detecção usa regressão linear e regras configuráveis executadas no backend. Não existe um modelo treinado de IA prevendo a hora da quebra. Os valores dos cenários de demonstração são programados; os alertas e ordens são calculados pelo fluxo real. A integração opcional com Gemini explica os dados, sem decidir sua gravidade ou abrir a OS.

A fórmula e as regras são explícitas no código; o resultado não é uma resposta fixa: depende dos valores, horários e configuração. Alguns parâmetros são configuráveis (janela, quantidade, duração, sensibilidade, R², persistência e sentido). Faixas de risco e fatores das opções de sensibilidade são regras fixas e documentadas. Não apresentar R² como probabilidade de falha ou a extrapolação como previsão garantida de quebra.

## Entendendo os 30 minutos

São a duração mínima **coberta pela amostra selecionada**, entre sua primeira e sua última medição. Não são um cronômetro iniciado ao abrir a tela, nem a frequência de atualização do frontend.

- Com histórico válido que já cubra o mínimo, a análise pode acontecer imediatamente.
- Sem esse histórico, o gráfico mostra cada leitura, mas a confirmação aguarda quantidade **e** tempo suficientes.
- A lista normal é consultada a cada 30 segundos; esse intervalo de consulta não altera o período mínimo de observação.
- O máximo de leituras limita a amostra. Cinquenta medições a cada segundo cobrem aproximadamente 49 segundos; não atingem 30 minutos nem após horas de coleta, pois a rotina seleciona as últimas 50.
- No sensor de demonstração, a duração mínima é **um minuto**, com sete medições, máximo de sete e intervalo de pelo menos dez segundos. Assim a primeira fase pode ser demonstrada em cerca de um minuto, sem falsificar timestamps.

Para ajustar um sensor real, selecionar equipamento/sensor e abrir **Ajustar tempo e critérios**. O formulário oferece atalhos de 1, 5 e 30 minutos. O perfil de 1 minuto prepara duração mínima de 1, mínimo de 7 leituras e máximo de 500, para comportar coleta frequente. Os atalhos apenas editam o formulário; a alteração vale ao salvar e fica específica do sensor. Não fabricam histórico, não reiniciam o relógio e não garantem um alerta. Recomenda-se o equipamento [DEMO] para a apresentação, preservando os critérios dos ativos reais.

## Como usar na apresentação

1. Atualizar o backend e aplicar `python manage.py migrate`. Entrar como administrador e abrir **Tendências**.
2. Expandir **Apresentação guiada · teste de tendência** e clicar em **Ativar modo de teste**.
3. Se o filtro global estiver em Todas as Empresas, escolher a empresa do teste. Caso contrário, usa a empresa global selecionada.
4. Manter **Aumento gradual** e clicar em **Iniciar demonstração**. O sistema cria e seleciona um equipamento e sensor identificados como [DEMO]. Não usa nem muda o sensor real que estava selecionado.
5. A página rola até o sensor selecionado ao iniciar a fase. Mostrar o gráfico azul crescendo, ainda abaixo da linha vermelha de limite superior. As primeiras leituras aparecem como **Aguardando dados**. Expor os indicadores de quantidade e tempo.
6. Aguardar aproximadamente um minuto, com a página visível. Na sétima leitura, os critérios devem ser atendidos pelo cenário crescente padrão. Mostrar os itens aprovados, o alerta de origem `tendencia`, sua descrição e a OS `preditiva` vinculada.
7. Explicar que o último valor é 52 °C, abaixo até da primeira faixa de aviso operacional (70 °C neste cadastro). A abertura é antecipada por tendência, não por ultrapassagem do limite.
8. Opcionalmente clicar em **Próxima fase: ultrapassar 100 °C** e acompanhar 60, 68, 76, 84, 92, 100 e 108 °C. A descrição distingue o alerta preditivo do alerta de origem `limite` e sua OS corretiva.
9. Clicar em **Próxima fase: recuperar e estabilizar**. Sete leituras em 40 °C substituem a amostra anterior; a tendência deixa de ser anormal e os alertas normalizam conforme os serviços existentes. As OS continuam pendentes: a recuperação do sensor não conclui o trabalho da equipe.
10. Para provar que o alerta não é forçado, criar outra demonstração com **Estável** ou **Pico isolado**. Cada demonstração possui seu próprio sensor; os registros anteriores não são apagados.

Manter o frontend e a API em execução e esta página visível. A alimentação é conduzida por chamadas do frontend; ao sair, ocultar a página ou desligar o modo de teste, não são enviadas novas leituras. O relógio continua real: ao retomar, pode haver intervalo maior entre medições, alterando o ritmo calculado. **Parar teste** muda também o estado no backend. **Retomar último teste** consulta a última demonstração do administrador e retoma a alimentação se ela ainda estiver em execução. Para um novo roteiro com intervalos regulares, usar uma nova demonstração.

## Contas fáceis para mostrar

Fase crescente ideal: 40 → 42 → 44 → 46 → 48 → 50 → 52 °C em intervalos de dez segundos. Há sete leituras e seis intervalos, totalizando um minuto.

```text
Ritmo ilustrativo = (52 − 40) / 1 minuto = 12 °C/minuto = 720 °C/hora
Tempo até o limite = (100 − 52) / 12 = 4 minutos, se o ritmo continuar
Persistência = 6 intervalos de subida / 6 intervalos = 100%
R² = 1 se os horários e valores estiverem perfeitamente alinhados
```

A aplicação usa regressão sobre **todas** as leituras e seus horários reais. Pequenas diferenças na cadência de rede podem produzir um ritmo e um prazo ligeiramente diferentes. O cálculo de minutos foi adicionado diretamente ao backend, evitando converter um valor em horas já arredondado para apresentar uma conta inexata.

O limite de sensibilidade média, com limite superior 100, é 2 °C/h. A subida do cenário é muito maior que isso e satisfaz os demais critérios. Uma projeção de poucos minutos recebe risco crítico pelas regras atuais (até duas horas), mas não prova que haverá uma quebra.

O cenário estável usa sete valores de 40 °C. O pico isolado usa seis valores de 40 e um de 65 °C: somente um dos seis intervalos sobe, abaixo de 70% de persistência. Ambos devem terminar sem alerta de tendência nem alerta por limite nessa configuração.

## Gráfico e explicação na página

- Com **Todos os equipamentos**, a visão geral continua sem desenhar vários gráficos.
- Ao selecionar um equipamento com um único sensor ativo, esse sensor é selecionado automaticamente. Com vários, a página pede escolher qual acompanhar. Selecionar um sensor quando o equipamento está em Todos também preenche seu equipamento.
- Um gráfico de leituras observadas usa os horários reais no eixo horizontal e inclui o limite superior na escala vertical, com linha vermelha tracejada. Assim a ultrapassagem fica visível e grandezas diferentes não são misturadas.
- O painel exibe quantidade/mínimo, duração/mínimo, ritmo em unidade/minuto, projeção em minutos, critérios aprovados e fórmula. Antes da suficiência, o ritmo aparece como aguardando amostra, não como uma conclusão estatística.
- As verificações vêm do backend (`checks`), usando as mesmas comparações da decisão. Os fatores e limiares não são recalculados no frontend para decidir a anomalia.
- O gráfico do detalhe também recebe o limite superior e é omitido quando repetiria o gráfico já selecionado acima.

## Implementação e API administrativa

Migração `telemetria/0003_trenddemo.py`: cria `TrendDemo`, com UUID, proprietário, sensor OneToOne, cenário, estado, passo, criação e horário da última leitura. Não altera as configurações dos sensores existentes nem a global.

Rotina em `telemetria/demo_service.py`, exposta por `telemetria/demo_views.py`:

| Método | Rota | Efeito |
|---|---|---|
| POST | `/api/telemetria/tendencias/demo/` | `empresa` e `cenario` opcional; cria equipamento/sensor/configuração próprios e primeira leitura |
| GET | `/api/telemetria/tendencias/demo/` | Última demonstração do administrador, ou null; sem novas leituras |
| GET | `/api/telemetria/tendencias/demo/<uuid>/` | Consulta uma demonstração do próprio administrador |
| POST | `/api/telemetria/tendencias/demo/<uuid>/` | `acao`: `avancar`, `parar` ou `fase`; fase aceita `cenario` |

Cenários aceitos: `aumento`, `limite`, `recuperacao`, `estavel`, `pico`. A resposta contém progresso, ids, análise atual, descrições dos alertas e ordens vinculadas. O cliente não escolhe valores, timestamps ou sensor de destino.

O backend exige `tipo_usuario=admin` e propriedade da demonstração para todas as ações, inclusive GET. Gestor e técnico não podem acionar a API, mesmo que modifiquem o frontend. O controle do modo de teste na interface é uma escolha de UX adicional; a autorização real está na API.

A criação bloqueia o proprietário e para outra execução daquele administrador, preservando seus registros. Avanço bloqueia a sessão na transação, respeita intervalo mínimo de dez segundos, grava no máximo uma nova leitura por chamada e limita a fase a sete valores. Repetir uma chamada antes da hora ou após conclusão não avança. Não há preenchimento retroativo de leituras perdidas. Após trinta minutos da criação, avanço para e novas fases exigem criar outra demonstração.

As gravações usam `Telemetria.objects.create`, portanto percorrem os sinais reais de tendência e de limite. Não se cria alerta ou OS diretamente na simulação, não se chama Gemini e não se falsifica relógio. O simulador contínuo geral passa a excluir sensores vinculados a demonstrações, para não misturar ruído aleatório com o roteiro guiado. Se ele já estava em execução antes da atualização, reinicie esse processo: scripts Python já iniciados não recarregam automaticamente a função alterada.

Novos campos de análise, aditivos: `checks` (rótulo e aprovação de cada critério), `threshold_per_hour`, `projected_breach_minutes`. Campos anteriores permanecem disponíveis. Alertas e OS de demonstração são registros reais ligados ao sensor [DEMO], visíveis nas telas normais. Novos testes não apagam os anteriores; contadores globais podem incluir outras demonstrações. Não há botão de limpeza destrutiva nesta entrega.

## Validação

- Dez testes de backend cobrem crescimento e antecedência, estabilidade/pico, limite versus tendência e recuperação, perfis, propriedade, entradas inválidas, relógio/valores controlados pelo servidor, parar/fases, expiração e isolamento do simulador.
- Teste PostgreSQL adicional verifica dois avanços simultâneos gerando um único passo.
- Vinte e cinco testes de frontend verificam também escala do gráfico/ultrapassagem, seleção única de sensor, ausência de gráficos em Todos, perfil rápido, proteção de ações, endpoints e encerramento do timer.
- Compilação do template Vue, sintaxe JavaScript e consistência de migrações fazem parte dos checks.
- Suíte explícita completa no PostgreSQL 18 descartável: **135 testes aprovados**, sem skips, incluindo concorrência do avanço da demonstração. O cluster local de testes foi encerrado após a execução.
- Suíte de frontend: **25 testes aprovados**, incluindo continuidade após renovação normal do token.
- Template Vue 3.4.21 compilado sem erros; `node --check`, `git diff --check` e `makemigrations --check --dry-run` aprovados.
- Migração `0003_trenddemo` aplicada com sucesso ao PostgreSQL de desenvolvimento; `showmigrations telemetria` confirmou as três migrações aplicadas. Não foram criados equipamentos de demonstração no banco de desenvolvimento durante a implementação: eles serão criados quando o administrador iniciar um teste.
- Sem nova conferência visual no navegador; a validação cobriu lógica, template e fluxo de banco, sem declarar aprovação visual.

A demonstração guiada é voltada ao funcionamento das tendências, não uma simulação física fiel de um motor. Os valores sobem rapidamente para caber na apresentação; essa aceleração é declarada, e os horários registrados continuam sendo reais.
