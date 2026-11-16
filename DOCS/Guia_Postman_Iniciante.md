# Testar o NanaSmart no Postman: guia para iniciantes

**Revisado em:** 16/11/2026. Exemplos conferidos nos URLs, serializers e regras atuais. Use uma base de demonstração autorizada: requisições de escrita alteram os dados selecionados.

## 1. Entender um pedido à API

Uma API é como o atendimento de uma oficina: você envia uma solicitação e recebe uma resposta. O Postman permite fazer esses pedidos sem usar a interface do NanaSmart.

| Parte do pedido | Exemplo | Significado |
|---|---|---|
| Método | `GET` | A operação pretendida. GET consulta; POST envia/cria; PATCH altera parte de um registro; DELETE exclui quando permitido. |
| Endereço | `{{base_url}}/api/equipamentos/` | O recurso consultado. |
| Cabeçalho | `Authorization: Bearer ...` | A credencial usada pela API. |
| Corpo JSON | `{"nome": "Motor"}` | Os dados enviados, quando a operação os exige. |

JSON usa aspas duplas para nomes e textos, números sem aspas, `true`/`false` para booleanos e `null` para ausência de valor. Não coloque vírgula depois do último campo.

## 2. Preparar o ambiente

1. Inicie o backend na raiz do projeto: `python manage.py runserver 127.0.0.1:9000`, após a configuração descrita no [README](../readme.md).
2. Crie uma coleção no Postman e uma variável `base_url` com o valor `http://127.0.0.1:9000`.
3. Crie também as variáveis `access_token` e `refresh_token`, inicialmente vazias.
4. No navegador, consulte `http://127.0.0.1:9000/api/schema/swagger-ui/` para os campos e operações disponíveis.

Nos exemplos, IDs como `1` são ilustrativos. Substitua pelos IDs retornados pelas consultas da sua base. Um ID válido de outra empresa pode não estar acessível ao seu usuário.

## 3. Fazer login e enviar o token

Envie `POST {{base_url}}/api/auth/login/`. Em **Body**, selecione **raw**, formato **JSON**, e informe:

```json
{"username": "seu_usuario", "password": "sua_senha"}
```

Copie `access` para a variável `access_token` e `refresh` para `refresh_token`. Na autorização dos pedidos protegidos, escolha Bearer Token e use `{{access_token}}`. Não duplique o prefixo `Bearer` no campo que já aplica esse tipo de autenticação.

Faça `GET {{base_url}}/api/auth/me/` para conferir o usuário, perfil e empresa. Para renovar a sessão, envie `POST {{base_url}}/api/auth/refresh/`:

```json
{"refresh": "{{refresh_token}}"}
```

Atualize `access_token` com o novo `access`. Os nomes atuais das rotas são `login/` e `refresh/`; os antigos caminhos `token/` não são os usados neste projeto.

## 4. Começar pelas consultas

| Pedido | O que verificar |
|---|---|
| `GET /api/equipamentos/` | Equipamentos permitidos ao perfil/empresa. |
| `GET /api/ordens-servico/?status=pendente` | Ordens pendentes que o usuário pode consultar. |
| `GET /api/ordens-servico/?prioridade=A` | Ordens de prioridade A, não alertas de nível crítico. |
| `GET /api/telemetria/sensores/` | Sensores autorizados e seus IDs. |
| `GET /api/telemetria/leituras/?sensor=1` | Leituras do sensor indicado. |
| `GET /api/alertas/?nivel=critico` | Ocorrências históricas que atingiram nível crítico. |

Acrescente `{{base_url}}` antes dos caminhos. Quando houver paginação, os itens ficam em `results` e `next` indica outra página.

## 5. Criar cadastros com o perfil adequado

Use administrador para criar empresas e gestor/admin autorizado para criar equipamentos da empresa. Consulte primeiro os IDs existentes para não repetir valores únicos como `cnpj` ou `numero_serie`.

Exemplo de equipamento em `POST /api/equipamentos/`:

```json
{
  "empresa": 1,
  "nome": "Motor de demonstração",
  "numero_serie": "DEMO-MOTOR-001",
  "tipo": "motor_eletrico",
  "horimetro": 500,
  "status": "ativo"
}
```

O exemplo deixa a criticidade sem avaliação. Para classificá-lo em A/B/C, a empresa precisa de critérios validados e a avaliação precisa de justificativa. Siga [Priorização ABC](PRIORIZACAO_ABC.md); não invente critérios apenas para preencher um campo.

Técnicos podem consultar equipamentos, mas não recebem permissão para criá-los por esse motivo. As regras variam conforme o recurso. A [estrutura da API](Estrutura_API.md) contém o catálogo atual.

## 6. Criar e atender uma ordem de serviço

Com gestor/admin da empresa, envie `POST /api/ordens-servico/`:

```json
{
  "equipamento": 1,
  "titulo": "Inspecionar rolamento",
  "descricao": "Ruído observado na inspeção visual do conjunto.",
  "tipo_os": "preventiva",
  "status": "pendente",
  "responsavel": null
}
```

**Não envie `prioridade` no cadastro ou PATCH comum da OS.** O servidor copia a criticidade vigente do equipamento na abertura. A prioridade será `A`, `B`, `C` ou ficará a definir. Valores antigos como `medio`/`critico` não são prioridades válidas da OS; enviar prioridade pelo CRUD é rejeitado.

Um técnico autorizado pode assumir uma ordem sem responsável da sua empresa com `PATCH /api/ordens-servico/1/`:

```json
{"responsavel": 5, "status": "andamento"}
```

Substitua `5` pelo ID do próprio técnico, consultado em `/api/auth/me/`. O técnico não pode atribuir a ordem a outra pessoa. Ordens de outro técnico não aparecem no seu escopo de consulta.

Para concluir, o responsável autorizado envia:

```json
{"status": "concluida"}
```

O servidor registra a conclusão e garante um histórico de manutenção. Uma OS concluída ou cancelada não deve ser reaberta alterando o status.

### Ajustar prioridade com justificativa

Gestor/admin usa `POST /api/ordens-servico/1/ajustar_prioridade/`:

```json
{"prioridade": "A", "justificativa": "Ajuste aprovado após avaliação do impacto operacional."}
```

Para restaurar a referência herdada, use `POST /api/ordens-servico/1/restaurar_prioridade/` com `justificativa`. O servidor preserva o histórico e rejeita alterações em ordens encerradas. Troque a justificativa ilustrativa pela avaliação real da equipe.

## 7. Completar o histórico existente

Depois de concluir a OS, consulte `GET /api/historico/?ordem_servico=1`. Anote o ID do histórico retornado e envie `PATCH /api/historico/{id}/`:

```json
{
  "descricao_servico": "Inspeção realizada e rolamento substituído.",
  "data_execucao": "2026-11-16",
  "custo_pecas": "250.00",
  "custo_mao_de_obra": "400.00"
}
```

A data e o relato são exemplos: use os dados do serviço executado. `custo_total` é calculado. Como a relação é um-para-um e a conclusão já garante o histórico, não faça outro POST para duplicar o registro da mesma OS. A escrita nesse recurso segue as permissões da API; gestor/admin pode completar os dados autorizados, enquanto técnico tem somente leitura nessa política.

## 8. Leituras e alertas

Gestor/admin autorizado pode enviar uma leitura em `POST /api/telemetria/leituras/`:

```json
{"sensor": 1, "valor": 90.0}
```

O horário `timestamp` é preenchido pelo servidor. A medição pode gerar ou atualizar alertas conforme os limites e critérios do sensor. Uma leitura isolada não garante uma tendência válida nem abertura de OS preditiva.

Alertas são **somente consulta**: use `GET /api/alertas/` e `GET /api/alertas/{id}/`. Não existe a etapa antiga de resolver um alerta com PATCH. O serviço registra a recuperação quando os critérios são satisfeitos; isso não conclui a OS. Um problema observado por uma pessoa deve entrar diretamente em uma ordem de serviço.

`nivel=baixo`, `medio` ou `critico` descreve o alerta. `prioridade=A`, `B` ou `C` descreve a OS. São classificações diferentes. Consulte [Histórico de alertas](HISTORICO_ALERTAS.md).

## 9. Plano por horímetro

Com gestor/admin, envie `POST /api/planos-manutencao/`:

```json
{
  "equipamento": 1,
  "nome_servico": "Troca de óleo",
  "descricao": "Executar o serviço previsto no plano da equipe.",
  "intervalo_horas": 100,
  "ativo": true
}
```

Não envie `prioridade` nem `horimetro_ultima_os`: são somente leitura na API. Se o equipamento tem 500 h ao criar o plano, o controle inicial fica em 500 h e o próximo disparo é 600 h. Um PATCH autorizado no equipamento que atualize o horímetro para esse patamar pode acionar o sinal e abrir a OS do plano. O código evita outra OS aberta para o mesmo plano pelo critério existente; a nova OS recebe a regra ABC da abertura.

## 10. IA, exportação e demonstração

| Operação | Como testar |
|---|---|
| Chat | `POST /api/gemini/chat/`, com `{"message":"Quais ordens precisam de atenção?"}`. Requer configuração do provedor para obter resposta real. |
| Análise individual | `POST /api/ordens-servico/1/analise-ia/`, sem corpo obrigatório, para uma OS autorizada. A resposta não é gravada na OS. |
| Exportação | `GET /api/exportar/equipamentos/csv/`; altere o formato para `excel` ou `pdf` e salve o conteúdo como arquivo. |
| Tendência | `GET /api/telemetria/tendencias/?sensor_id=1`; consulte os critérios e parâmetros na documentação específica. |

O retorno de IA indisponível depende do endpoint: a análise individual usa 503; as views Gemini podem retornar uma mensagem informativa. Não presuma um único código para todos os endpoints de IA. Veja [Análise individual](ANALISE_OS_IA.md) e [Demonstração de tendências](DEMONSTRACAO_TENDENCIAS.md).

## 11. Interpretar as respostas

| Código | Significado frequente | O que conferir |
|---|---|---|
| 200 / 201 | Consulta/alteração bem-sucedida ou criação. | Corpo retornado e IDs reais. |
| 400 | Dados inválidos. | Mensagens dos campos; prioridade não pode ser enviada no CRUD da OS. |
| 401 | Autenticação ausente, inválida ou expirada. | Login, Bearer Token e renovação. |
| 403 | Operação não autorizada. | Perfil e permissões do recurso. |
| 404 | Objeto inexistente ou fora do escopo. | ID, empresa e responsável. |
| 405 | Método não oferecido pela rota. | Por exemplo, tentativa de PATCH no histórico de alertas. |
| 502 / 503 | Falha ou indisponibilidade na análise individual de OS. | Configuração e retorno do provedor. |

## 12. Conferência final

Teste uma consulta com cada perfil, confirme o recorte por empresa e tente acessar um objeto fora do seu escopo. Confira que técnico não escreve em sensores/leituras, que prioridade da OS só muda pela ação própria e que alertas não aceitam edição manual. Os resultados dependem dos registros e usuários existentes; os exemplos não criam automaticamente uma base de testes.

Os testes automatizados e suas limitações estão no [índice da documentação](README.md#verificação-da-revisão-de-16112026). Versões antigas dos fluxos não devem substituir este roteiro.
