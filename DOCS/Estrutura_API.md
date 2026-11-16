# API do NanaSmart

**Revisão:** 16/11/2026. O catálogo de rotas abaixo foi conferido no schema gerado pelo código local. Os campos de entrada e saída são definidos pelos serializers; a lista de modelos e campos persistidos está em [Banco de dados](DOCUMENTACAO_BANCO.md).

## Como consultar o contrato completo

Com o backend em `127.0.0.1:9000`, abra `/api/schema/swagger-ui/`, `/api/schema/redoc/` ou `/api/schema/`. O [README](../readme.md) explica a inicialização, e o [guia Postman](Guia_Postman_Iniciante.md) mostra exemplos de chamadas.

O catálogo registra as operações existentes. Ter uma operação listada não significa que todo perfil possa executá-la: permissões, empresa e objeto consultado também são verificados.

## Autenticação e acesso

Use `POST /api/auth/login/` com `username` e `password`. O retorno contém `access` e `refresh`. Envie `Authorization: Bearer SEU_ACCESS` nos recursos protegidos. Para renovar, use `POST /api/auth/refresh/` com `refresh`.

`GET /api/auth/me/` consulta o perfil. A troca de senha usa `senha_atual`, `nova_senha` e `confirmar_nova_senha` em `POST /api/auth/change-password/`.

Administradores têm escopo global; gestores trabalham com a própria empresa. Técnicos consultam os recursos operacionais permitidos e as ordens da própria empresa atribuídas a eles ou sem responsável. Técnicos não recebem, por isso, autorização para escrever em todos os recursos que consultam. O cadastro de empresas é reservado ao administrador; gestores podem consultar e alterar a própria empresa, conforme as permissões da view.

## Regras que afetam as chamadas

| Assunto | Comportamento atual | Referência |
|---|---|---|
| Criticidade e prioridade | Categorias `A`, `B`, `C` ou ausência de avaliação. A OS herda a criticidade na abertura. `prioridade` não é enviada no CRUD da OS; ajustes usam ações próprias com justificativa. | [Priorização ABC](PRIORIZACAO_ABC.md) |
| Alertas | Somente consulta. Não há criação, edição, exclusão ou resolução manual pela API de alertas. Leituras e serviços automáticos registram os episódios. | [Histórico de alertas](HISTORICO_ALERTAS.md) |
| OS e recuperação | Concluir/cancelar OS não resolve o alerta. Normalização do sensor não conclui manutenção. Estados terminais não são reabertos pelo fluxo normal. | [Histórico de alertas](HISTORICO_ALERTAS.md) |
| Histórico de manutenção | Uma conclusão garante um histórico por OS. Para completar um histórico já criado, consulte seu ID e altere o registro existente. | [Modelos do banco](DOCUMENTACAO_BANCO.md) |
| Planos por horímetro | `horimetro_ultima_os` e `prioridade` são somente leitura na API. A prioridade legada do plano não define a prioridade de novas OS. | [Priorização ABC](PRIORIZACAO_ABC.md) |
| Tendências | A consulta de tendência calcula o resultado; ingestão de leituras e comando periódico fazem a sincronização operacional. A IA é opcional. | [Identificação de tendências](IDENTIFICACAO_TENDENCIAS.md) |
| Análise individual de OS | `POST /api/ordens-servico/{id}/analise-ia/` usa a OS autorizada, sem salvar a resposta na OS. Indisponibilidade usa 503 e falha do provedor/resposta vazia usa 502. | [Análise de OS por IA](ANALISE_OS_IA.md) |
| Exportação | Formatos registrados: `csv`, `excel`, `pdf`. Famílias criam gerador e metadados, o catálogo é compartilhado por processo e um decorator registra a geração. MIME, extensão, autorização e recorte por empresa foram preservados. | [Factory Method](docs_padroes_projeto/Verificacao_Padroes_GoF_Verdes.md#3-factory-method) |

O campo `nivel` de alerta usa `baixo`, `medio`, `critico`. Ele não é a prioridade ABC da OS. `Sensor.tipo` e `Telemetria.timestamp` são os nomes persistidos atuais; nomes antigos como `tipo_sensor` e `data_hora` não devem ser assumidos como campos do contrato.

## Catálogo de rotas

Os métodos foram obtidos dos `paths` do OpenAPI gerado nesta revisão. `HEAD` e `OPTIONS` podem ser fornecidos pelo framework e não são enumerados nesta tabela. Parâmetros entre chaves devem ser substituídos pelo identificador correspondente.

| Rota | Métodos documentados |
|---|---|
| `/api/alertas/` | GET |
| `/api/alertas/{id}/` | GET |
| `/api/auth/change-password/` | POST |
| `/api/auth/login/` | POST |
| `/api/auth/me/` | GET, PATCH |
| `/api/auth/refresh/` | POST |
| `/api/criterios-criticidade/` | GET, POST |
| `/api/criterios-criticidade/atual/` | GET |
| `/api/criterios-criticidade/{id}/` | GET |
| `/api/dashboards/kpis/` | GET |
| `/api/dashboards/resumo/` | GET |
| `/api/empresas/` | GET, POST |
| `/api/empresas/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/equipamentos/` | GET, POST |
| `/api/equipamentos/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/exportar/alertas/{formato}/` | GET |
| `/api/exportar/dashboard/{formato}/` | GET |
| `/api/exportar/equipamentos/{formato}/` | GET |
| `/api/exportar/historico/{formato}/` | GET |
| `/api/exportar/ordens-servico/{formato}/` | GET |
| `/api/exportar/telemetria/{formato}/` | GET |
| `/api/gemini/chat/` | POST |
| `/api/gemini/gestao/financeira/` | POST |
| `/api/gemini/ordens/analise/` | POST |
| `/api/gemini/ordens/sem-atribuicao/` | POST |
| `/api/gemini/prompts/` | GET |
| `/api/gemini/prompts/analise-os/` | GET, PATCH |
| `/api/gemini/prompts/analise-os/reset/` | POST |
| `/api/gemini/prompts/{id}/` | GET, POST, PATCH |
| `/api/gemini/prompts/{id}/reset/` | POST |
| `/api/gemini/tendencia/` | POST |
| `/api/historico-criticidade/` | GET |
| `/api/historico-criticidade/{id}/` | GET |
| `/api/historico/` | GET, POST |
| `/api/historico/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/localizacao/` | GET, POST |
| `/api/localizacao/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/ordens-servico/` | GET, POST |
| `/api/ordens-servico/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/ordens-servico/{id}/ajustar_prioridade/` | POST |
| `/api/ordens-servico/{id}/analise-ia/` | POST |
| `/api/ordens-servico/{id}/historico_prioridade/` | GET |
| `/api/ordens-servico/{id}/restaurar_prioridade/` | POST |
| `/api/planos-manutencao/` | GET, POST |
| `/api/planos-manutencao/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/schema/` | GET |
| `/api/telemetria/leituras/` | GET, POST |
| `/api/telemetria/leituras/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/telemetria/sensores/` | GET, POST |
| `/api/telemetria/sensores/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/telemetria/tendencias/` | GET |
| `/api/telemetria/tendencias/demo/` | GET, POST |
| `/api/telemetria/tendencias/demo/{demo_id}/` | GET, POST |
| `/api/telemetria/trend-config/` | GET, POST |
| `/api/telemetria/trend-config/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/tipos-equipamento/` | GET, POST |
| `/api/tipos-equipamento/{id}/` | GET, PUT, PATCH, DELETE |
| `/api/usuarios/` | GET, POST |
| `/api/usuarios/{id}/` | GET, PUT, PATCH, DELETE |

Catálogo desta revisão: **59 caminhos e 110 operações documentadas**. Para dados de exemplo, campos obrigatórios, filtros, paginação e respostas, use o schema local. O catálogo é uma fotografia do código em 16/11/2026 e deve ser atualizado quando as rotas mudarem.

## Filtros, paginação e códigos de resposta

Listagens podem devolver um objeto paginado com `count`, `next`, `previous` e `results`. Não presuma que o conteúdo de uma página represente todos os registros autorizados.

Os filtros são específicos de cada recurso. O histórico de alertas compartilha seus filtros com a exportação. A ordenação ABC das ordens é feita no servidor antes da paginação. Consulte os documentos funcionais para os parâmetros vigentes.

Respostas frequentes: 200 para consultas/alterações, 201 para criação, 204 para exclusão autorizada sem corpo, 400 para dados inválidos, 401 para autenticação ausente/recusada, 403 para operação proibida e 404 para objeto inexistente ou fora do escopo. A rota pode definir outros códigos, como 405 para métodos não oferecidos.

## Verificação do contrato

O teste `app.test_schema` foi incluído na suíte de 292 testes desta revisão. A documentação do catálogo foi obtida com `SchemaGenerator`, sem gravar dados. Isso não equivale a chamar cada endpoint em produção. Para reproduzir a validação do schema, veja o [README](../readme.md#testes-e-verificações).
