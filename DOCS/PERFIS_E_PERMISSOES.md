# Perfis e permissões

Revisão: 17/11/2026. O perfil **operador** tem acesso básico de acompanhamento e abertura manual de solicitações. Todas as permissões são conferidas no backend, inclusive em chamadas diretas à API. O menu é reduzido ao mesmo escopo.

| Recurso | Operador | Técnico | Gestor | Administrador |
|---|---|---|---|---|
| Equipamentos e localizações | Consulta básica da própria empresa | Consulta da própria empresa | Gerencia na própria empresa | Gerencia globalmente |
| Alertas | Consulta de resumos da própria empresa | Consulta da própria empresa | Consulta da própria empresa | Consulta global |
| Abrir O.S. manual | Corretiva pendente, sem responsável | Conforme regras de atendimento | Sim, na própria empresa | Sim |
| Consultar e atender O.S. | Sem acesso à fila, detalhe ou ações | Atribuídas a si ou sem responsável, na própria empresa | Gerencia na própria empresa | Gerencia globalmente |
| Prioridade da O.S. | Herdada automaticamente; não ajusta | Consulta | Ajusta com justificativa | Ajusta com justificativa |
| Planos, tipos, critérios e histórico de criticidade | Sem acesso | Consulta | Gerencia na própria empresa | Gerencia globalmente |
| Telemetria, sensores, tendências e configuração | Sem acesso | Consulta | Gerencia na própria empresa | Gerencia; configuração global e demonstração |
| Dashboard, custos e exportações | Sem acesso | Conforme regras operacionais existentes | Conforme escopo da empresa | Global |
| Chat e análises de IA | Sem acesso | Recursos técnicos | Recursos técnicos e gerenciais | Recursos administrativos |
| Empresas e usuários | Sem acesso | Sem acesso | Usuários da própria empresa; consulta/edita a própria empresa | Gerencia globalmente |
| Próprio perfil e troca de senha | Sim | Sim | Sim | Sim |

O perfil não concede privilégios exclusivos: os demais perfis continuam com suas permissões anteriores. O operador possui apenas o subconjunto básico acima, com abertura manual de O.S. Não pode ser atribuído como responsável de atendimento, nem por gestor ou administrador via API. Perfis desconhecidos não recebem acesso operacional. Sem empresa vinculada, as consultas básicas retornam listas vazias e a abertura de ordem é recusada.

## Abertura manual pelo operador

Na interface, entre em **Equipamentos → Abrir O.S. manual** ou abra um equipamento e use o mesmo botão. Informe equipamento, título, descrição e, se aplicável, risco de segurança. O sistema confirma o número da ordem. O atendimento fica com a manutenção; o operador não recebe acesso à fila, ao detalhe das ordens ou a seus custos.

```http
POST /api/ordens-servico/
Authorization: Bearer <token-do-operador>
Content-Type: application/json
```

```json
{
  "equipamento": 1,
  "titulo": "Ruído no motor",
  "descricao": "Ruído observado durante a operação.",
  "risco_seguranca": true
}
```

Resposta: HTTP 201, com `id`, equipamento, título, descrição, risco, `tipo_os=corretiva`, `status=pendente`, prioridade e data de abertura. A prioridade copia a criticidade vigente; equipamento ainda não avaliado gera prioridade nula, para triagem da manutenção. A ordem não recebe alerta ou evidência preditiva automática.

Somente os quatro campos do exemplo são aceitos como entrada; `risco_seguranca` é opcional. Campos adicionais, incluindo `responsavel`, `status`, `tipo_os`, `prioridade`, custos e datas, causam HTTP 400 e não criam a ordem. Equipamento de outra empresa também causa HTTP 400. Consultar, editar, excluir, ajustar prioridade ou gerar análise de IA de uma ordem retorna HTTP 403 para o operador.

As consultas de equipamentos não retornam critérios, representantes de validação ou histórico gerencial. As consultas de alertas retornam identificação, equipamento/sensor, origem, descrição, nível, status e horários; não retornam análises de IA, evidências internas ou vínculo de O.S. A indicação do sensor no resumo não concede acesso ao cadastro ou às leituras do sensor.

## Cadastro, banco e dados de demonstração

- `tipo_usuario` aceita `admin`, `gestor`, `tecnico` e `operador`. Novos usuários sem perfil explícito recebem `operador`, inclusive no formulário de cadastro. `createsuperuser` usa `admin`.
- Administradores e gestores autorizados podem cadastrar operadores pela API; gestores mantêm o isolamento da própria empresa. O formulário de usuários do administrador inclui a nova opção.
- Para atualizar a base, execute `python manage.py migrate`. A migração `accounts.0002` preserva os perfis existentes e altera apenas as opções/padrão e o manager do usuário.
- `scripts/seed_db.py` gera um operador por empresa, além do gestor e dos técnicos. O padrão é cinco funcionários (um gestor, três técnicos e um operador); `--funcionarios` tem mínimo três e inclui o operador no total. O resumo informa seu login; a senha é `123`.
- O comando auxiliar `popular_usuarios` também conhece o perfil. O seed completo continua sendo a referência de demonstração. Sua execução apaga dados; não é necessária para habilitar o operador em uma base existente.

## Verificação

`accounts.test_operador` cobre login, perfil padrão, superusuário, isolamento entre empresas, respostas reduzidas, bloqueios por endpoint, tentativa de elevação de perfil, ausência de empresa, abertura manual válida, campos proibidos e impedimento de atribuir operador. Os testes do frontend em `FrontATT/telemetria.test.cjs` verificam login sem consultas administrativas, navegação reduzida, ausência de polling de tendências e envio apenas dos campos permitidos na O.S. Os testes do seed incluem a recusa do dashboard ao operador.

```powershell
python manage.py test accounts.test_operador telemetria.test_seed_demo telemetria.test_seed_telemetry --settings=app.test_settings --noinput
node --test FrontATT/telemetria.test.cjs
```
