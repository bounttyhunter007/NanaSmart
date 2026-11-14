# Demonstração de tendências: gráfico, alerta e OS

Revisão: 13/11/2026. Roteiro de apresentação e descrição da implementação. Complementa [Identificação de tendências](IDENTIFICACAO_TENDENCIAS.md) e [Telemetria e UX](TELEMETRIA_UX.md).

## O que dizer ao apresentar

> Uma leitura informa o valor atual. A tendência mede a direção e o ritmo de mudança ao longo do tempo. O sistema verifica se há leituras suficientes, tempo de observação, repetição e consistência antes de recomendar uma inspeção.
>
> A detecção usa regressão linear e regras configuráveis executadas no backend. Não existe um modelo treinado de IA prevendo a hora da quebra. Os valores dos cenários de demonstração são programados; os alertas e ordens são calculados pelo fluxo real. A integração opcional com Gemini explica os dados, sem decidir sua gravidade ou abrir a OS.

A fórmula e as regras são explícitas no código; o resultado não é uma resposta fixa: depende dos valores, horários e configuração. Alguns parâmetros são configuráveis (janela, quantidade, duração, sensibilidade, R², persistência e sentido). Faixas de risco e fatores das opções de sensibilidade são regras fixas e documentadas. Não apresentar R² como probabilidade de falha ou a extrapolação como previsão garantida de quebra.

## Entendendo o histórico mínimo

O novo padrão de duas horas é a duração mínima **coberta pela amostra selecionada**, entre sua primeira e sua última medição. Não são um cronômetro iniciado ao abrir a tela, nem a frequência de atualização do frontend.

- Com histórico válido que já cubra o mínimo, a análise pode acontecer imediatamente.
- Sem esse histórico, o gráfico mostra cada leitura, mas a confirmação aguarda quantidade **e** tempo suficientes.
- A lista normal é consultada a cada 30 segundos; esse intervalo de consulta não altera o período mínimo de observação.
- O máximo de leituras limita a amostra. Cinquenta medições a cada segundo cobrem aproximadamente 49 segundos. Se houver histórico suficiente, a rotina distribui leituras reais no tempo e também verifica as originais; sem histórico suficiente, não inventa duração.
- No sensor de demonstração, a duração mínima é **um minuto**, com sete medições, máximo de sete e intervalo de pelo menos dez segundos. Assim a primeira fase pode ser demonstrada em cerca de um minuto, sem falsificar timestamps.

Para ajustar um sensor real, selecionar equipamento/sensor e abrir **Ajustar análise**. O formulário destaca histórico mínimo e antecedência da O.S. em ajustes independentes; sugestões de tempo apenas preparam o formulário e passam a valer ao salvar. Critérios adicionais ficam em opções avançadas. A demonstração conserva seu perfil próprio de um minuto e sete leituras.

## Como usar na apresentação

1. Atualizar o backend e aplicar `python manage.py migrate`. Entrar como administrador e abrir **Tendências**.
2. Expandir **Apresentação guiada · teste de tendência** e clicar em **Ativar modo de teste**.
3. Se o filtro global estiver em Todas as Empresas, escolher a empresa do teste. Caso contrário, usa a empresa global selecionada.
4. Manter **Aumento gradual** e clicar em **Iniciar demonstração**. O sistema cria e seleciona o equipamento Motor de monitoramento e seu sensor Temperatura do motor, identificados pelo vínculo com a sessão de teste. Não usa nem muda o sensor real que estava selecionado.
5. A página rola até o sensor selecionado ao iniciar a fase. Mostrar o gráfico azul crescendo, ainda abaixo da linha vermelha de limite superior. As primeiras leituras aparecem como **Aguardando dados**. Expor os indicadores de quantidade e tempo.
6. Aguardar aproximadamente um minuto, com a página visível. Na sétima leitura, os critérios devem ser atendidos pelo cenário crescente padrão. Mostrar os itens aprovados, o alerta de origem `tendencia`, sua descrição e a OS `preditiva` vinculada.
7. Explicar que o último valor é 52 °C, abaixo até da primeira faixa de aviso operacional (70 °C neste cadastro). A abertura é antecipada pela previsão confirmada de alcance do limite dentro da antecedência configurada. A O.S. registra essa previsão e suas evidências.
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

Novos campos de análise, aditivos: `checks` (rótulo e aprovação de cada critério), `threshold_per_hour`, `projected_breach_minutes`. Campos anteriores permanecem disponíveis. Alertas e OS de demonstração são registros reais ligados ao sensor vinculado à sessão de teste, visíveis nas telas normais. Novos testes não apagam os anteriores; contadores globais podem incluir outras demonstrações. Não há botão de limpeza destrutiva nesta entrega.

## Validação

- Testes de backend cobrem crescimento, antecedência, estabilidade/pico, limite versus tendência, recuperação, perfis, propriedade, entradas inválidas, relógio/valores controlados pelo servidor, parar/fases, expiração e isolamento do simulador.
- PostgreSQL verifica concorrência de ingestão, análise preditiva e avanço da demonstração, sem duplicação.
- Testes de frontend cobrem seleção única, busca, filtros, tempos independentes, gráfico ao vivo/operacional e encerramento dos timers.
- Compilação Vue, schema OpenAPI, migrações e verificação visual em desktop e celular complementam a suíte.
