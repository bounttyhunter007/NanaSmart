# Classificação de equipamentos e prioridade de OS

Atualizado em 06/11/2026.

## Regra operacional

| Categoria | Equipamento | Ordem de serviço |
|---|---|---|
| A | Alta criticidade | Alta prioridade |
| B | Média criticidade | Média prioridade |
| C | Baixa criticidade | Baixa prioridade |
| `null` | Não avaliada | A definir |

A criticidade representa o impacto da falha. Cada empresa define seus critérios considerando segurança, ambiente, produção, qualidade, redundância e recuperação. A classificação é uma decisão justificada da equipe, com critérios validados pelo representante da manutenção. A [IEC 60812:2018](https://webstore.iec.ch/en/publication/26359) é uma referência para análise das consequências e criticidade; esta tabela ABC é uma convenção local, não uma tabela universal prescrita pela norma, nem uma declaração de certificação.

Na abertura, toda OS copia a categoria vigente do equipamento. A regra vale para corretivas, preventivas e preditivas, incluindo alertas, tendências e planos por horímetro. O servidor registra classe, justificativa e revisão dos critérios daquele momento. Ausência de avaliação não impede abertura: a OS fica **A definir** para revisão do gestor.

Gravidade, risco de segurança e agravamento dos sensores permanecem visíveis, mas não alteram a prioridade automaticamente. Uma mudança na criticidade do equipamento só afeta novas ordens. Uma OS já aberta só muda de prioridade por ajuste explícito de gestor/admin, com justificativa e histórico. Não há prazos de atendimento universais ou SLA inferidos pela categoria.

## Uso na interface

1. Em **Equipamentos → Critérios ABC da empresa**, gestor/admin escolhe a empresa e preenche os critérios A/B/C, o nome de quem os validou na manutenção e a data. A data não pode ser futura. Os textos sugeridos não contam como validação.
2. Publicar cria uma revisão imutável. Revisões anteriores e avaliações que as utilizam são preservadas. Não é necessário que o representante tenha conta no sistema; o gestor registra a validação realizada pela equipe.
3. No cadastro do equipamento, consultar os critérios, selecionar a classe e justificar a avaliação. Sem guia validado, pode-se salvar como não avaliado. O tipo do catálogo só sugere uma classe; **Aceitar classe sugerida** é uma ação explícita que também exige justificativa.
4. O detalhe do equipamento mostra classe, justificativa, revisão utilizada e histórico com autor/data. Alterar a justificativa também registra uma avaliação; não se reescrevem avaliações anteriores.
5. A lista de OS abre em **Abertas**, com tabela no computador e cartões no celular. As colunas separam prioridade da OS e criticidade atual do equipamento. A ordem é A, B, C e A definir, depois abertura mais antiga e ID, antes da paginação.
6. **Prioridade e histórico** permite consultar o motivo e o retrato da abertura. Gestor/admin ajusta a prioridade ou restaura a referência herdada na abertura, sempre com motivo. Técnico apenas consulta. OS concluídas ou canceladas não aceitam revisão de prioridade.

O equipamento da OS é fixo após abertura. Um vínculo incorreto deve ser corrigido cancelando a ordem e abrindo outra. A empresa de um equipamento também permanece fixa para preservar a atribuição dos critérios e do histórico.

## API

Todas as rotas exigem autenticação e respeitam o isolamento por empresa. Administradores podem atuar em todas as empresas; gestores e técnicos ficam restritos à sua empresa. Técnicos só consultam OS próprias ou sem responsável, inclusive nas exportações e no histórico de prioridade.

### Critérios

- `GET /api/criterios-criticidade/atual/?empresa=ID`: revisão vigente, ou sugestões com `revisao: null`, sem gravar nada. Para usuários com empresa vinculada, o parâmetro pode ser omitido.
- `GET /api/criterios-criticidade/?empresa=ID`: revisões publicadas, paginadas.
- `GET /api/criterios-criticidade/ID/`: consulta de uma revisão.
- `POST /api/criterios-criticidade/`: publica uma nova revisão, exclusivo de gestor/admin. Não existem edição ou exclusão de revisões pela API.

Campos de publicação: `empresa`, `criterio_a`, `criterio_b`, `criterio_c`, `representante_manutencao` e `data_validacao` (`YYYY-MM-DD`). Todos são obrigatórios. Revisão, autor e data de registro são atribuídos no servidor; um bloqueio por empresa evita revisões duplicadas em publicações concorrentes.

### Equipamentos

As rotas de equipamentos são mantidas. `criticidade` aceita A/B/C ou `null`. Uma classificação ou mudança na avaliação exige `justificativa_criticidade` preenchida. `criterios_criticidade` é somente leitura e aponta para a revisão vigente usada na avaliação; `criterios_utilizados` apresenta os textos dessa revisão.

O campo opcional de escrita `aceitar_sugestao: true` aceita a classe de `tipo_equipamento`, sem inferir classe pelo nome. `criticidade_sugerida` é informativo. Informar o catálogo sem aceitar sua sugestão não classifica o equipamento.

`GET /api/historico-criticidade/?equipamento=ID` consulta exclusivamente o histórico desse equipamento. Preserva classe anterior/nova, motivo, autor, data, origem, revisão e os dados anteriores da avaliação.

### Ordens de serviço

Na criação, não envie `prioridade`. O servidor define e devolve:

- `prioridade`: A/B/C ou `null`;
- `prioridade_origem`: `herdada`, `ajustada` ou `convertida`;
- `prioridade_automatica`: referência da abertura, preservada para restauração;
- `prioridade_herdada_conhecida`: indica se a referência é de uma herança comprovada;
- `prioridade_manual`: indica ajuste explícito;
- `criticidade_na_abertura`, `justificativa_criticidade_na_abertura`, `criterios_criticidade_na_abertura` e `criterios_abertura`: retrato imutável;
- `criticidade_atual`, `equipamento_nome`, `responsavel_nome`: informações para comparação na fila.

Enviar `prioridade` no POST/PUT/PATCH geral retorna 400 com orientação para usar a ação específica. Os demais metadados são somente leitura. Não se transforma um salvamento comum nem o encerramento em ajuste manual.

```http
POST /api/ordens-servico/42/ajustar_prioridade/
Content-Type: application/json

{"prioridade": "A", "justificativa": "Antecipar atendimento durante a parada da linha."}
```

```http
POST /api/ordens-servico/42/restaurar_prioridade/
Content-Type: application/json

{"justificativa": "Retomar o planejamento registrado na abertura."}
```

As duas ações retornam a OS atualizada. Exigem gestor/admin, OS aberta e motivo não vazio. A restauração usa a referência da abertura, inclusive `null` quando o equipamento ainda não era avaliado; não consulta a classe atual do equipamento. Legados sem herança comprovada exigem ajuste explícito.

`GET /api/ordens-servico/42/historico_prioridade/` é paginado e registra herança, ajustes, restaurações e conversão do legado. O registro inclui valores anterior/novo, motivo, autor e data.

`GET /api/ordens-servico/` aceita os filtros existentes, mais `prioridade=A|B|C|a_definir`. `abertas=true`, busca, responsável, equipamento, setor, tipo e empresa são combináveis. A resposta paginada inclui `a_definir` (total pendente nos filtros atuais) e `total_escopo` (total visível ao usuário, antes dos filtros). Filtros e ordenação são os mesmos na exportação de OS; o dashboard usa a mesma precedência ABC dentro de seus grupos.

O campo `prioridade` de planos é preservado como legado, somente leitura na API, e não determina a prioridade de novas ordens. Clientes que antes enviavam prioridade no formulário geral da OS devem migrar para as ações acima.

## Conversão de dados existentes

As migrações novas não reescrevem migrações iniciais e não apagam ordens ou avaliações.

- Equipamentos e sugestões de tipo: A/B/C permanecem; D passa a C. O valor anterior da sugestão fica em `criticidade_padrao_legada`.
- OS e referência automática: Crítica/Alta → A, Média → B, Baixa → C. Valores ausentes ou desconhecidos ficam `null`, preservados na auditoria.
- Cada equipamento classificado e cada OS recebem registro da conversão com os valores originais. Motivos, responsáveis, status, datas e retratos da abertura permanecem intactos. Históricos antigos são identificados como legado; D ainda pode aparecer nesses registros.
- Não se associa retrospectivamente um guia validado a uma avaliação antiga. O gestor deve registrar os critérios da empresa antes de fazer novas avaliações.
- A matriz antiga não comprova herança da classe; por isso, OS convertidas recebem `prioridade_herdada_conhecida=false`. A referência automática antiga é preservada e convertida para consulta, mas não habilita restauração como se fosse uma herança.
- A reversão das conversões recupera os valores originais a partir dos registros de migração. Fazer backup antes de qualquer migração de ambiente.

## Verificação

As suítes cobrem classificação justificada, revisões imutáveis, validação de datas, sugestões explícitas, autorização/empresas, herança em todas as origens, preservação após reclassificação/agravamento, ajuste/restauração, encerramento, paginação e exportação consistente, além da migração dos registros legados.

```powershell
.\.venv\Scripts\python.exe manage.py test accounts authentication ativos telemetria alertas manutencao exportacao gemini_api.tests --settings=app.test_settings --noinput
node --test FrontATT/abc.test.cjs FrontATT/telemetria.test.cjs FrontATT/live-chart.test.cjs
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=app.test_settings
```

O SQLite usa banco descartável e ignora testes que exigem bloqueios PostgreSQL. Os testes de concorrência devem ser executados também em banco PostgreSQL descartável, separado do desenvolvimento. Não utilizar scripts de população destrutiva para validar a interface.

O trabalho não altera instruções, modelos ou o acionamento da IA. O leitor de contexto existente apenas passa a aceitar prioridade nula como “A definir”.
