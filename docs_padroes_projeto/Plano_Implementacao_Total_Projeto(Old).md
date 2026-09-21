# Plano de implementação total do projeto NanaSmart

## 1. Objetivo

Este plano tem como finalidade evoluir o projeto de forma segura, sem quebrar a API atual, preservando a compatibilidade com o front-end e mantendo a documentação de toda mudança.

A prioridade é:

1. manter todas as rotas atuais funcionando
2. não quebrar o comportamento atual da aplicação
3. documentar qualquer rota nova antes da integração com o front-end
4. melhorar a arquitetura interna do projeto
5. facilitar a geração de um diagrama de classes claro e consistente do projeto

---

## 2. Regras gerais do plano

### Regra 1 — não quebrar a API existente

Toda rota já existente deve continuar funcionando. O front-end atual depende do contrato atual, e qualquer alteração de rota, payload ou resposta deve ser tratada como mudança de contrato.

### Regra 2 — novas rotas só entram com documentação

Se for necessário criar nova rota, ela deve:

- ser documentada em Swagger/ReDoc
- constar na documentação da API
- manter a rota antiga ativa quando houver compatibilidade possível
- ter justificativa técnica clara
- ser explicada em termos de intenção, uso e impacto

### Regra 3 — refatoração interna antes de mudança de front-end

A melhoria da arquitetura deve acontecer no backend antes do front-end. O front-end só deve receber mudanças quando a API estiver estabilizada e documentada.

### Regra 4 — documentação obrigatória para cada evolução

Toda mudança de arquitetura, padrão, endpoint, método ou classe deve ser documentada com os seguintes elementos:

- como era
- o que motivou a mudança
- por que foi feita
- como foi feita
- como ficou
- em qual arquivo foi implementada
- em qual linha ou região principal
- qual impacto no sistema
- qual risco de regressão
- como testar

---

## 3. Estrutura do projeto e foco de implementação

### 3.1. Módulos principais

- [app](../app)
- [accounts](../accounts)
- [authentication](../authentication)
- [ativos](../ativos)
- [alertas](../alertas)
- [telemetria](../telemetria)
- [manutencao](../manutencao)
- [exportacao](../exportacao)
- [gemini_api](../gemini_api)
- [FrontATT](../FrontATT)

### 3.2. O que já existe e deve ser preservado

- arquitetura Django + DRF
- módulos por domínio
- relacionamento por modelos e serializers
- autenticação JWT em [app/settings.py](../app/settings.py)
- estrutura de exportação em [exportacao](../exportacao)
- builder para prompts em [gemini_api](../gemini_api)
- sinais em [alertas/signals.py](../alertas/signals.py), [telemetria/signals.py](../telemetria/signals.py) e [ativos/signals.py](../ativos/signals.py)
- multi-tenant e permissões em [accounts/permissions.py](../accounts/permissions.py)

---

## 4. Ordem de implementação

## Fase 1 — Inventário e contrato atual da API

### Objetivo

Mapear o que o sistema já expõe e como o front-end consome isso.

### O que fazer

1. listar todos os endpoints existentes em:
   - [app/urls.py](../app/urls.py)
   - [authentication/views.py](../authentication/views.py)
   - [accounts](../accounts)
   - [ativos](../ativos)
   - [alertas](../alertas)
   - [telemetria](../telemetria)
   - [manutencao](../manutencao)
   - [exportacao](../exportacao)
   - [gemini_api](../gemini_api)

2. identificar:
   - rota
   - método HTTP
   - payload de entrada
   - payload de saída
   - permissões esperadas
   - regras de empresa/tenant
   - dependências do front-end

3. separar endpoints em categorias:
   - estáveis
   - refatoráveis sem risco
   - novos e opcionais
   - críticos

### Documento obrigatório para cada endpoint

- nome do endpoint
- rota atual
- módulo
- arquivo
- responsável
- payload de entrada
- payload de saída
- autorização
- risco de mudança
- necessidade de compatibilidade

### Resultado esperado

- inventário completo da API atual
- noções claras de quais endpoints podem ser alterados e quais precisam ser preservados

---

## Fase 2 — Preservação total da API pública

### Objetivo

Garantir que o backend continue compatível enquanto se aprimora a arquitetura interna.

### Princípios

- não remover rotas antigas sem compatibilidade
- não alterar parâmetros sem migração
- não mudar o formato de retorno sem evolução controlada
- qualquer nova funcionalidade deve ser adicionada sem impactar o contrato antigo

### Regra prática

Se a rota atual retorna JSON específico para o front-end, a nova implementação deve preservar esse mesmo formato até que o front-end seja atualizado.

### Documentação obrigatória

Para cada rota preservada, registrar em documentação:

- rota antiga
- rota nova opcional
- formato antigo
- formato novo
- compatibilidade
- status de migração

---

## Fase 3 — Revisão da arquitetura por módulo

## 3.1. Módulo de autenticação e contas

Arquivos principais:

- [accounts/models.py](../accounts/models.py)
- [accounts/permissions.py](../accounts/permissions.py)
- [authentication/views.py](../authentication/views.py)

### Como está

- autenticação com JWT e sessão
- permissões por perfil
- multi-tenant por empresa e por usuário

### O que deve ser feito

- centralizar regras de permissão em policies ou factories
- evitar lógica repetida em diversas views
- manter as rotas existentes sem quebrar o contrato

### Padrão que pode ser usado

- Factory Method para criação de políticas por perfil
- Builder em alguns casos de montagem de payloads de resposta

### Documento de mudança exigido

- antes: lógica acoplada em views e permissões
- agora: centralização por tipo de perfil
- arquivo principal afetado
- impact no front-end
- teste de regressão

---

## 3.2. Módulo de ativos

Arquivos principais:

- [ativos/models.py](../ativos/models.py)
- [ativos/signals.py](../ativos/signals.py)
- [ativos/views.py](../ativos/views.py)

### Como está

- equipamentos com empresa, localização, planos de manutenção e criticidade
- alguns gatilhos de atualização e regras de negócio

### O que deve ser feito

- padronizar criação e atualização de equipamentos
- evitar regras espalhadas em signals e views
- organizar melhor a criação de planos de manutenção e posicionamento da empresa

### Padrões sugeridos

- Factory Method para tipos de equipamento ou tipos de manutenção
- Builder para montar relatórios e payloads de dashboard de ativos

### Documento de mudança exigido

- como era o fluxo
- como fica o fluxo novo
- qual regra foi movida para serviço
- qual arquivo foi alterado
- impacto em listagens, filtros e dashboards

---

## 3.3. Módulo de manutenção

Arquivos principais:

- [manutencao/models.py](../manutencao/models.py)
- [manutencao/views.py](../manutencao/views.py)
- [manutencao/permissions.py](../manutencao/permissions.py)
- [manutencao/dashboards/views.py](../manutencao/dashboards/views.py)

### Como está

- o sistema cria ordens de serviço com tipos e prioridades
- há dashboards com KPIs e indicadores de manutenção
- existem regras por usuário e permissões

### O que deve ser feito

- padronizar criação de OS por tipo
- criar factory para tipos de ordem de serviço
- manter a API pública estável
- centralizar a lógica de KPI e dashboards em componentes específicos

### Padrões sugeridos

- Factory Method para tipos de manutenção e OS
- Builder para payload de dashboard

### Documento de mudança exigido

- como era para criação de OS
- como ficou
- em qual arquivo a criação foi abstraída
- quais rotas continuam iguais
- quais rotas poderão surgir de forma complementar

---

## 3.4. Módulo de alertas e telemetria

Arquivos principais:

- [alertas/models.py](../alertas/models.py)
- [alertas/signals.py](../alertas/signals.py)
- [telemetria/models.py](../telemetria/models.py)
- [telemetria/signals.py](../telemetria/signals.py)
- [telemetria/views.py](../telemetria/views.py)

### Como está

- telemetria gera alertas com base em limites
- alertas podem criar ordens de serviço
- há lógica automática e reativa com sinais

### O que deve ser feito

- manter signal como gatilho
- mover regras de negócio para serviços específicos
- separar criação de alerta, priorização e geração de ordem
- evitar que o signal se torne uma caixa preta de lógica

### Padrões sugeridos

- Observer-like via signals (já está funcionando)
- Factory Method para criação de alertas e ações por tipo
- Builder para mensagens e payloads de alerta

### Documento de mudança exigido

- como a telemetria disparava alertas antes
- como ela deve disparar depois
- qual regra foi extraída para serviço
- quantos gatilhos continuam ativos
- riscos de regressão

---

## 3.5. Módulo de exportação

Arquivos principais:

- [exportacao/views.py](../exportacao/views.py)
- [exportacao/utils/base_exporter.py](../exportacao/utils/base_exporter.py)
- [exportacao/utils/exporter_factory.py](../exportacao/utils/exporter_factory.py)
- [exportacao/utils/csv_exporter.py](../exportacao/utils/csv_exporter.py)
- [exportacao/utils/excel_exporter.py](../exportacao/utils/excel_exporter.py)
- [exportacao/utils/pdf_exporter.py](../exportacao/utils/pdf_exporter.py)

### Como está

- exportação em CSV, Excel e PDF já foi estruturada com Factory Method
- a view delega a criação do exportador

### O que deve ser feito

- continuar mantendo o contrato atual
- se for necessário exportar novos tipos de dados, manter a fábrica e a interface base
- não quebrar o nome da rota atual ou os formatos esperados

### Padrões sugeridos

- Factory Method está correto
- Builder para composição de relatório final pode ser adicionado sem quebrar as rotas

### Documento de mudança exigido

- como era o exportador antes
- como ficou com o factory
- qual arquivo foi alterado
- qual padrão foi aplicado
- como testar em CSV, Excel e PDF

---

## 3.6. Módulo de IA / Gemini

Arquivos principais:

- [gemini_api/views.py](../gemini_api/views.py)
- [gemini_api/prompt_builder.py](../gemini_api/prompt_builder.py)
- [gemini_api/prompt_builder_pattern.py](../gemini_api/prompt_builder_pattern.py)
- [gemini_api/prompt_director.py](../gemini_api/prompt_director.py)
- [gemini_api/prompt.py](../gemini_api/prompt.py)

### Como está

- há builder para prompt
- há diretor para montar blocos
- a IA já é separada de forma mais organizada

### O que deve ser feito

- manter o builder
- expandir para mais tipos de prompt sem prejudicar o front-end
- garantir que qualquer nova rota de IA seja documentada antes da integração

### Padrões sugeridos

- Builder
- Factory Method para diferentes tipos de análise/serviço de IA (se surgir necessidade)

### Documento de mudança exigido

- antes: concatenação manual
- agora: montagem por builder e director
- arquivo principal da refatoração
- por que isso melhorou manutenção
- impacto em respostas do chat e dashboards

---

## 4. Como aplicar cada padrão no projeto real

## 4.1. Builder

### Quando usar

- construção de payloads complexos
- textos de chat/IA
- relatórios e dashboards
- mensagens de alerta

### Onde aplicar

- [gemini_api/prompt_builder_pattern.py](../gemini_api/prompt_builder_pattern.py)
- [manutencao/dashboards/views.py](../manutencao/dashboards/views.py)
- [exportacao/views.py](../exportacao/views.py)

### Como aplicar

- criar etapas de montagem
- usar `reset()`, `com_...()` e `build()`
- manter o objeto final encapsulado

### Documentação esperada

- como era a construção manual
- como ficou com Builder
- qual arquivo foi criado/alterado
- qual objetivo da refatoração

---

## 4.2. Factory Method

### Quando usar

- criação dinâmica de objetos por tipo
- diferentes tipos de OS
- diferentes tipos de relatório
- diferentes tipos de permissão

### Onde aplicar

- [exportacao/utils/exporter_factory.py](../exportacao/utils/exporter_factory.py)
- [manutencao/models.py](../manutencao/models.py)
- [manutencao/views.py](../manutencao/views.py)
- [accounts/permissions.py](../accounts/permissions.py)

### Como aplicar

- definir interface comum
- registrar tipos em um dicionário ou mapa
- instanciar por tipo

### Documentação esperada

- como o código era com condicionais
- como fica com fábrica
- por que ficou melhor
- quais rotas continuam iguais

---

## 4.3. Abstract Factory

### Quando usar

- quando houver famílias relacionadas de produtos e múltiplos contextos simultâneos

### Situação no projeto

Ainda não é prioridade.

### Deixar claro no documento

- não será implementado na fase atual
- só será considerado em expansão real do sistema

---

## 4.4. Singleton

### Quando usar

- quase nunca, e neste projeto não deve ser usado

### Motivos

- ambiente Django multi-process
- risco de contaminação entre testes
- mudança de configuração em runtime
- acoplamento global

### Como documentar

- por que foi descartado
- em quais arquivos se evitou a criação
- como a aplicação deve manter configuração e dependências em vez de estado global

---

## 5. Documentação obrigatória para o diagrama de classes

Para permitir a construção de um diagrama de classes fácil e didático, toda implementação deve ser registrada em um formato padronizado.

### Template de documentação por classe/módulo

#### 1. Nome da classe

#### 2. Arquivo

- caminho do arquivo
- referência para a linha principal ou bloco principal

#### 3. Finalidade

- para que existe
- qual problema resolve

#### 4. Como era antes

- descrição do código anterior
- problema do código antigo
- por que era difícil manter

#### 5. Como foi feito

- padrão aplicado
- comportamento principal
- entrada e saída
- interações com outras classes

#### 6. Como ficou

- estrutura final
- responsabilidades separadas
- vantagem da nova estrutura

#### 7. Relações

- com quem se relaciona
- quais objetos/serviços dependem dela
- qual padrão de composição ou agregação ela usa

#### 8. Impacto no projeto

- o que melhorou
- o que foi preservado
- o que ainda precisa evoluir

#### 9. Teste e validação

- como checar se continua funcionando
- rotas ou cenários de teste

---

## 6. Estrutura mínima de documentação por arquivo

Para cada arquivo importante, o projeto deve manter uma documentação resumida com as seguintes seções:

- nome do arquivo
- objetivo
- classe principal
- funções principais
- padrões usados
- como era
- como ficou
- dependências
- onde é consumido
- risco de regressão

### Exemplos de arquivos que devem receber esse registro

- [app/settings.py](../app/settings.py)
- [app/urls.py](../app/urls.py)
- [accounts/models.py](../accounts/models.py)
- [accounts/permissions.py](../accounts/permissions.py)
- [authentication/views.py](../authentication/views.py)
- [ativos/models.py](../ativos/models.py)
- [alertas/signals.py](../alertas/signals.py)
- [telemetria/signals.py](../telemetria/signals.py)
- [manutencao/models.py](../manutencao/models.py)
- [manutencao/permissions.py](../manutencao/permissions.py)
- [exportacao/views.py](../exportacao/views.py)
- [exportacao/utils/exporter_factory.py](../exportacao/utils/exporter_factory.py)
- [gemini_api/prompt_builder_pattern.py](../gemini_api/prompt_builder_pattern.py)
- [gemini_api/prompt_director.py](../gemini_api/prompt_director.py)

---

## 7. Checklist de implementação

### Prioridade alta

- [ ] inventariar todas as rotas e contratos atuais
- [ ] preservar todas as rotas existentes
- [ ] revisar [app/urls.py](../app/urls.py)
- [ ] revisar [app/settings.py](../app/settings.py)
- [ ] revisar [accounts/permissions.py](../accounts/permissions.py)
- [ ] revisar [manutencao/permissions.py](../manutencao/permissions.py)
- [ ] revisar [exportacao](../exportacao)
- [ ] revisar [gemini_api](../gemini_api)

### Prioridade média

- [ ] implementar ou reforçar Builder em payloads e prompts
- [ ] ampliar Factory Method em manutenção e permissões
- [ ] refinar sinais em alertas e telemetria
- [ ] ajustar dashboards em [manutencao/dashboards/views.py](../manutencao/dashboards/views.py)

### Prioridade baixa

- [ ] avaliar Abstract Factory somente se houver família real de produtos
- [ ] confirmar que Singleton continua fora do projeto

---

## 8. Estratégia de documentação para o front-end

### Regras

- o front-end não deve ser alterado antes da documentação da API
- qualquer endpoint novo precisa ter documentação e exemplo de uso
- qualquer rota alterada precisa informar impacto e detalhes de migração
- o front-end deve receber uma versão estável pois agora já há documentação de compatibilidade

### Entregável mínimo

- lista de endpoints atuais
- lista de endpoints novos
- status de compatibilidade
- exemplos de payload
- exemplos de resposta
- observações de segurança e empresa

---

## 9. O que deve ser preservado até o fim da implementação

- estrutura de módulos
- workflows de manutenção
- regras de multi-tenant
- autenticação e autorização
- exportação em CSV/Excel/PDF
- prompts de IA
- dados em telemetria e alertas
- compatibilidade da API já existente

---

## 10. Status da implementação aplicada

A implementação do plano foi iniciada e aplicada de forma segura em pontos estratégicos do backend, mantendo compatibilidade com as rotas já existentes.

### 10.1. Centralização de permissões por política

Foi criada a fábrica de políticas de acesso em [accounts/permission_policies.py](../accounts/permission_policies.py), com a intenção de concentrar a regra de autorização por perfil, em vez de espalhar comparações diretas em cada view ou classe de permissão.

O comportamento anterior ficava disperso em [accounts/permissions.py](../accounts/permissions.py), onde cada classe verificava manualmente `tipo_usuario` e métodos HTTP. Agora a regra foi encapsulada em políticas específicas: `GestorPolicy`, `TecnicoPolicy`, `GestorOrReadOnlyPolicy` e `AuthenticatedNoDeleteForTecnicoPolicy`.

Esse ajuste foi aplicado sem mudar a API pública já existente: a classe de permissão continua expondo a mesma interface do DRF (`has_permission`), mas agora delega a decisão para a fábrica de políticas.

### 10.2. Impacto prático

- o código passou a seguir a estratégia de Factory Method para decidir a política adequada por perfil
- a lógica de autorização ficou mais legível e testável
- a manutenção futura pelo front-end e pelo backend fica mais segura
- o contrato do sistema atual continua estável

### 10.3. Validação executada

Os testes focados foram executados com o Django e o resultado foi positivo:

- `accounts.tests` passou com 6 testes executados
- 0 falhas
- 0 issues do sistema reportados pelo `manage.py test`

A validação confirma que a refatoração de permissões não quebrou o comportamento da API atual.

---

## 11. Conclusão do plano

Este plano tem como foco principal a evolução segura do projeto sem quebrar o backend e a API.

A estratégia é simples e objetiva:

- preservar a API existente
- evoluir por refatoração interna
- aplicar padrões úteis sem exagero
- documentar cada passo
- preparar o projeto para geração de um diagrama de classes claro e didático
- só então ajustar o front-end

Esse método reduz risco, melhora a arquitetura e mantém o sistema prático para uso real.

---

## 12. Observação final sobre documentação

Este plano deve ser tratado como documentação viva do projeto. Sempre que uma mudança for feita, deve ser registrado:

- o que era
- por que era necessário
- como foi feito
- o que mudou
- em qual arquivo
- qual linha ou região principal do código
- como testes e validações foram realizados
- como isso impacta o front-end

Apenas assim será possível montar um diagrama de classes simples, didático e fiel ao que realmente foi implementado no projeto.
