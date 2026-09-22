# Documento de análise e implementação dos 4 padrões de projeto no NanaSmart

## 1. Objetivo deste documento

Este documento atualiza a análise dos 4 padrões de projeto do projeto NanaSmart, agora com foco no repositório inteiro e não apenas no módulo de Gemini.

Os padrões analisados são:

1. Builder
2. Factory Method
3. Abstract Factory
4. Singleton

O objetivo aqui não é apenas justificar o uso de padrões, mas também apontar:

- onde cada padrão já está sendo usado
- onde ele deve ser implementado no restante do projeto
- como o projeto está hoje
- como ele deve evoluir
- o que precisa ser feito em cada módulo
- como a arquitetura deve ficar após a implementação

---

## 2. Visão geral do projeto

O NanaSmart é um sistema Django de gestão de manutenção industrial com os seguintes módulos principais:

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

A arquitetura real do projeto combina:

- Django MVC/MVT
- API REST com DRF
- isolamento multi-tenant por empresa
- sinais de evento (Observer-like)
- regras de negócio em views, models e sinais
- exportação em múltiplos formatos
- integração com IA Gemini

Portanto, a análise de padrões precisa considerar o sistema como um todo e não apenas a camada de IA.

---

## 3. Diagnóstico do estado atual do repositório

### 3.1. Onde o projeto já está bem estruturado

#### a) Exportação

Arquivos principais:

- [exportacao/views.py](../exportacao/views.py)
- [exportacao/utils/base_exporter.py](../exportacao/utils/base_exporter.py)
- [exportacao/utils/exporter_factory.py](../exportacao/utils/exporter_factory.py)
- [exportacao/utils/csv_exporter.py](../exportacao/utils/csv_exporter.py)
- [exportacao/utils/excel_exporter.py](../exportacao/utils/excel_exporter.py)
- [exportacao/utils/pdf_exporter.py](../exportacao/utils/pdf_exporter.py)

Como está:

- há uma interface base para exportadores
- há uma fábrica para decidir o tipo de exportador
- as views usam a fábrica ao invés de if/elif direto
- o padrão Factory Method já está implementado na prática

Como deve ficar:

- cada exporter encapsula sua lógica interna
- a view apenas delega a criação
- a fábrica continua centralizando o registro dos formatos aceitos

---

#### b) IA / prompts

Arquivos principais:

- [gemini_api/prompt_builder_pattern.py](../gemini_api/prompt_builder_pattern.py)
- [gemini_api/prompt_director.py](../gemini_api/prompt_director.py)
- [gemini_api/prompt.py](../gemini_api/prompt.py)
- [gemini_api/prompt_builder.py](../gemini_api/prompt_builder.py)

Como está:

- existe Builder para compor prompts por blocos
- existe Director para definir a ordem dos blocos
- existe Prompt encapsulando o texto final
- a construção do texto deixou de ser manual e repetitiva

Como deve ficar:

- cada tipo de prompt deve ter um fluxo definido no Director
- o Builder deve continuar acumulando blocos e retornando self
- a função de prompt deve apenas chamar o Builder e transformar em texto final

---

#### c) Sinais de eventos

Arquivos principais:

- [alertas/signals.py](../alertas/signals.py)
- [telemetria/signals.py](../telemetria/signals.py)
- [ativos/signals.py](../ativos/signals.py)

Como está:

- a telemetria dispara alerta quando o valor entra fora do limite
- o alerta pode gerar ordem de serviço
- existe uma cadeia automática de eventos

Como deve ficar:

- essa cadeia deve continuar sendo tratada como um mecanismo de observação/ação
- a regra de negócio deve permanecer centralizada para evitar lógica espalhada
- todas as ações automáticas devem ser explícitas e rastreáveis

---

#### d) Autenticação e permissões

Arquivos principais:

- [accounts/permissions.py](../accounts/permissions.py)
- [accounts/models.py](../accounts/models.py)
- [authentication/views.py](../authentication/views.py)
- [manutencao/permissions.py](../manutencao/permissions.py)

Como está:

- há separação por perfil
- há regras de leitura/escrita por papel do usuário
- há filtros por empresa e permissões

Como deve ficar:

- essa lógica deve continuar centralizada em policies/permissões
- se surgir um crescimento maior, pode ser necessário mover parte dessas regras para factories ou estratégias

---

### 3.2. Onde o projeto ainda está mais acoplado

Há alguns pontos do projeto em que a lógica ainda está muito direta e pode ser melhorada com padrões:

#### a) Views que montam dados em código manual

Exemplos:

- [exportacao/views.py](../exportacao/views.py)
- [manutencao/dashboards/views.py](../manutencao/dashboards/views.py)
- [gemini_api/prompt_builder.py](../gemini_api/prompt_builder.py)

Problema:

- a montagem do resultado final está espalhada em várias etapas do código
- há lógica repetida para montar cabeçalho, filtros, colunas, blocos e texto

Como melhorar:

- usar Builder para composição dos dados finais
- usar Factory Method para escolha do tipo de dado ou relatório
- separar plano de montagem de geração final

---

#### b) Lógica de regras de negócio distribuída em sinais e views

Exemplos:

- [alertas/signals.py](../alertas/signals.py)
- [telemetria/signals.py](../telemetria/signals.py)
- [ativos/signals.py](../ativos/signals.py)

Problema:

- algumas regras estão espalhadas em vários pontos
- a evolução do sistema pode tornar essa lógica difícil de manter

Como melhorar:

- centralizar a criação de eventos em serviços específicos
- manter o signal apenas como gatilho
- mover regras de negócio para classes ou funções de serviço

---

#### c) Criação de objetos por tipo em vários módulos

Exemplos:

- [manutencao/models.py](../manutencao/models.py)
- [telemetria/models.py](../telemetria/models.py)
- [ativos/models.py](../ativos/models.py)

Problema:

- certos objetos têm múltiplos fluxos de criação
- a diferença entre tipos de manutenção ou tipo de alerta pode crescer

Como melhorar:

- usar Factory Method para criar objetos ou ações conforme o tipo
- separar as regras por tipo em classes específicas

---

## 4. Análise dos 4 padrões no repositório inteiro

## 4.1. Builder

### Decisão

Builder deve continuar sendo usado.

### Onde ele já é importante

- [gemini_api/prompt_builder_pattern.py](../gemini_api/prompt_builder_pattern.py)
- [gemini_api/prompt_director.py](../gemini_api/prompt_director.py)
- [gemini_api/prompt_builder.py](../gemini_api/prompt_builder.py)

### Onde ele também deve ser usado no resto do projeto

#### 1. Montagem de relatórios de exportação

Arquivos:

- [exportacao/views.py](../exportacao/views.py)
- [exportacao/utils](../exportacao/utils)

Como fazer:

- criar um componente de relatório builder
- adicionar etapas como:
  - com_titulo()
  - com_colunas()
  - com_filtros()
  - com_dados()
  - com_rodape()
  - build()

O que isso resolve:

- elimina concatenação manual de dados
- padroniza o objeto final
- facilita criação de relatórios em CSV, Excel e PDF

Como vai ficar:

- a view apenas chama a fábrica para obter o exporter
- o exporter usa o builder para montar o conteúdo do documento

---

#### 2. Montagem de dashboards

Arquivos:

- [manutencao/dashboards/views.py](../manutencao/dashboards/views.py)

Como fazer:

- criar um DashboardBuilder
- montar blocos como resumo executivo, KPI, alertas e tendências
- incluir blocos condicionalmente

O que isso resolve:

- garante consistência na resposta dos dashboards
- evita código repetitivo
- facilita múltiplas visões executivas

---

#### 3. Construção de respostas automatizadas da IA

Arquivos:

- [gemini_api/views.py](../gemini_api/views.py)
- [gemini_api/prompt_builder.py](../gemini_api/prompt_builder.py)

Como fazer:

- manter o PromptBuilderConcreto como padrão
- evoluir o Director para cobrir também casos extras como tendência e análise financeira

O que isso resolve:

- melhora manutenção
- reduz duplicação em múltiplos tipos de prompt

---

### Conclusão sobre Builder

Builder é um padrão essencial para o projeto, especialmente em:

- IA
- dashboards
- relatórios
- payloads de resposta
- montagem de mensagens de alerta

---

## 4.2. Factory Method

### Decisão

Factory Method deve continuar sendo usado e ampliado.

### Onde ele já está bem usado

- [exportacao/utils/exporter_factory.py](../exportacao/utils/exporter_factory.py)
- [exportacao/views.py](../exportacao/views.py)

### Onde ele deve ser implementado no restante do projeto

#### 1. Criação de tipos de manutenção

Arquivos:

- [manutencao/models.py](../manutencao/models.py)
- [manutencao/views.py](../manutencao/views.py)

Como fazer:

- criar uma fábrica para tipos de OS:
  - corretiva
  - preventiva
  - preditiva
- cada tipo retorna uma implementação com regras próprias de criação, prioridade e estratégia de acompanhamento

O que isso resolve:

- elimina ifs para cada tipo de OS
- centraliza a regra de criação
- melhora manutenção futura

---

#### 2. Criação de relatórios por tipo

Arquivos:

- [exportacao/views.py](../exportacao/views.py)
- [manutencao/dashboards/views.py](../manutencao/dashboards/views.py)

Como fazer:

- criar uma fábrica para tipos de relatório:
  - dashboard geral
  - manutenção
  - alertas
  - telemetria
  - financeiro

O que isso resolve:

- padroniza os retornos
- cada tipo de relatório segue uma interface comum

---

#### 3. Criação de policies por perfil de usuário

Arquivos:

- [accounts/permissions.py](../accounts/permissions.py)
- [manutencao/permissions.py](../manutencao/permissions.py)

Como fazer:

- criar uma fábrica de policies por tipo de usuário
- cada perfil devolve a política correta de leitura/escrita

O que isso resolve:

- evita lógica repetitiva em cada view
- facilita manutenção e escalabilidade

---

### Conclusão sobre Factory Method

Este padrão é um dos mais valiosos para o projeto inteiro, porque ele resolve criação dinâmica de objetos e comportamentos por tipo.

Ele já está bem implementado em exportação e pode ser expandido para:

- ordens de serviço
- alertas
- relatórios
- dashboards
- regras de permissão

---

## 4.3. Abstract Factory

### Decisão

Abstract Factory ainda não é necessário.

### Justificativa

O projeto não apresenta famílias de produtos fortemente relacionadas e interdependentes em múltiplos contextos.

Hoje, o Factory Method atende bem às necessidades.

### Onde seria útil apenas no futuro

Só faria sentido se o projeto expandisse para:

- diferentes modelos de relatórios por empresa
- diferentes famílias de dashboards para setores ou clientes
- diferentes “kits” de gestão para tipos distintos de operação industrial

Exemplo:

- família A: manutenção operacional
- família B: manutenção financeira
- família C: manutenção estratégica

Cada família teria seu conjunto de relatórios, dashboards e IA associada.

### Conclusão

Para o estado atual, Abstract Factory não é recomendado. A complexidade extra não traz benefício proporcional.

---

## 4.4. Singleton

### Decisão

Singleton não deve ser usado neste projeto.

### Justificativa

O projeto é baseado em Django, onde o estado global é perigoso e pouco adequado para aplicações com múltiplos processos, autenticação dinâmica e testes isolados.

### Onde ele seria perigoso

- cliente global de Gemini
- cache global compartilhado
- configuração global mutável
- conexão global de banco

### Como o projeto deve lidar com isso

- usar contexto e parâmetros de execução
- passar dependências por função ou classe
- manter configuração em settings
- usar objetos de serviço sem estado global

### Conclusão

Singleton deve continuar fora do projeto.

---

## 5. Como o projeto está hoje e como deve ficar

### 5.1. Estado atual

Hoje o projeto já possui:

- arquitetura básica em Django
- módulos por domínio
- regras de negócio em sinais e views
- exportação por factory
- builder para prompts de IA
- autenticação e permissões por perfil
- multi-tenant em vários endpoints

### 5.2. Estado desejado

O projeto deve evoluir para uma arquitetura mais organizada:

- Builder para montagem de payloads complexos
- Factory Method para criação por tipo
- regras de negócio mais centralizadas em serviços
- sinais usados apenas como gatilhos e não como lógica principal
- views mais enxutas
- módulos mais coesos e menos acoplados

### 5.3. Efeito esperado

Com essa evolução, o projeto terá:

- menos duplicação
- menos acoplamento
- melhor testabilidade
- melhor manutenção
- escalabilidade melhor
- maior clareza na arquitetura

---

## 6. Onde exatamente implementar cada padrão no repositório

### Builder

Implementar em:

- [gemini_api/prompt_builder_pattern.py](../gemini_api/prompt_builder_pattern.py)
- [gemini_api/prompt_director.py](../gemini_api/prompt_director.py)
- [gemini_api/prompt_builder.py](../gemini_api/prompt_builder.py)
- [exportacao/views.py](../exportacao/views.py)
- [manutencao/dashboards/views.py](../manutencao/dashboards/views.py)

### Factory Method

Implementar em:

- [exportacao/utils/exporter_factory.py](../exportacao/utils/exporter_factory.py)
- [manutencao/models.py](../manutencao/models.py)
- [manutencao/views.py](../manutencao/views.py)
- [accounts/permissions.py](../accounts/permissions.py)
- [manutencao/permissions.py](../manutencao/permissions.py)

### Abstract Factory

Não implementar agora.

### Singleton

Não implementar.

---

## 7. O que precisa ser feito de fato

### 7.1. Para o módulo de exportação

- continuar padronizando a interface de exportação
- garantir que todos os exportadores tenham a mesma assinatura
- manter a fábrica registrando por formato
- manter as views desacopladas da lógica de criação

### 7.2. Para o módulo de IA

- manter o Builder como base da montagem de prompt
- expandir o Director para cobrir todos os cenários relevantes
- remover concatenação manual quando possível
- evitar mistura de lógica de geração de texto com lógica de negócio

### 7.3. Para o módulo de manutenção

- separar criação de ordem por tipo
- padronizar priorização e criação automática
- usar Factory Method para tipos de manutenção

### 7.4. Para o módulo de alertas e telemetria

- manter signals como gatilhos
- mover regras específicas para serviços
- padronizar criação de alertas e ações subsequentes

### 7.5. Para autenticação e permissões

- padronizar política por perfil
- centralizar regra de acesso
- evitar ifs repetidos em cada view

### 7.6. Para app e arquitetura geral

- manter os módulos separados por domínio
- manter configuração no [app/settings.py](../app/settings.py)
- evitar acoplamento entre módulo de IA e aplicação operacional

---

## 8. Plano prático de implementação

### Fase 1 - consolidar o que já existe

- manter e validar o Builder para prompts
- manter a Factory Method para exportação
- revisar a interface comum de exportadores

### Fase 2 - aplicar em manutenção e alertas

- criar factory para tipos de OS
- padronizar criação de alertas e regras de prioridade
- reduzir lógica espalhada em sinais

### Fase 3 - aplicar em dashboards e relatórios

- implementar Builder de payload de dashboard
- implementar factory de relatórios
- centralizar formato do retorno

### Fase 4 - aplicar em permissão e acesso

- criar policies por perfil
- padronizar permissões em todas as views

### Fase 5 - refinar arquitetura

- remover duplicações
- reduzir acoplamento
- aumentar coesão por módulo

---

## 9. Conclusão final

Os 4 padrões analisados são importantes para o projeto, mas com diferentes graus de necessidade.

- Builder: essencial para montagem de texto e payloads complexos
- Factory Method: altamente relevante e já aplicado em exportação
- Abstract Factory: não é necessário neste momento
- Singleton: não deve ser usado

Além disso, o projeto inteiro não pode ser entendido como “apenas Gemini”. A arquitetura real do NanaSmart envolve vários domínios e fluxos:

- manutenção
- ativos
- alertas
- telemetria
- autenticação
- exportação
- IA
- dashboards

A implementação correta dos padrões deve acontecer em todo esse conjunto, e não apenas na camada de IA.

O caminho ideal é:

- manter Factory Method na exportação
- manter Builder em prompts e montagem de dados complexos
- reforçar a organização por módulos
- evitar Singleton
- usar signals apenas como gatilhos
- ampliar Factory Method para criação por tipo de manutenção, relatório e permissão

Esse modelo torna o sistema mais limpo, mais fácil de evoluir e mais consistente com a arquitetura real do projeto.

---

## 10. Verificação de ambiente

Foi realizada a validação do ambiente com Django:

- comando executado: python manage.py check
- resultado: falhou por ausência de dependência do projeto local
- evidência: ModuleNotFoundError: No module named 'django'

Isso significa que a análise arquitetural do código foi feita com base no repositório, mas a execução real do projeto ainda depende da instalação do ambiente Django antes de validar runtime completo.
