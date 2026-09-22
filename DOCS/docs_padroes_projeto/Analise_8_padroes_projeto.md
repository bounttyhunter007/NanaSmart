# ANÁLISE ARQUITETURAL — 8 PADRÕES DE PROJETO
## NanaSmart — Plataforma de Manutenção Industrial Preditiva

**Documento**: Análise detalhada da aplicação dos 8 padrões de projeto  
**Data**: Setembro 2024  
**Fase**: FASE 1 — ANÁLISE (SEM MODIFICAÇÕES DE CÓDIGO)  
**Status**: Relatório completo para aprovação

---

## 📑 SUMÁRIO EXECUTIVO

Após análise completa do repositório NanaSmart, identificamos:

- ✅ **3 padrões já implementados corretamente** e funcionando bem
- ⚠️ **2 padrões com implementação parcial** que podem ser reestruturados
- ❌ **3 padrões sem casos de uso seguros** no escopo atual
- 🎯 **Recomendação geral**: Reestruturar Facades existentes e não forçar padrões artificiais

| Padrão | Status | Ação |
|--------|--------|------|
| **Abstract Factory** | ✅ Implementado | Manter |
| **Factory Method** | ✅ Implementado | Manter |
| **Builder** | ✅ Implementado | Manter |
| **Singleton** | ❌ Não aplicável | Não implementar |
| **Facade** | ⚠️ Parcial | Reestruturar |
| **Adapter** | ⚠️ Parcial | Reestruturar |
| **Composite** | ❌ Não aplicável | Não implementar |
| **Decorator** | ❌ Não aplicável | Não implementar |

---

## 1. VISÃO GERAL DO PROJETO

### 1.1 Propósito do Sistema

**NanaSmart** é uma **plataforma completa de manutenção industrial preditiva** que:

- Gerencia **ativos (equipamentos) industriais** com múltiplas métricas
- Coleta **telemetria em tempo real** via sensores IoT
- Gera **alertas automáticos** quando parâmetros saem do normal
- Cria e gerencia **ordens de serviço** (manutenção corretiva, preventiva e preditiva)
- Integra **Inteligência Artificial** (Google Gemini) para análise e suporte
- Exporta **relatórios em múltiplos formatos** (CSV, Excel, PDF)
- Implementa **isolamento multi-tenant** — cada empresa só vê seus próprios dados

### 1.2 Principais Características

| Aspecto | Descrição |
|--------|-----------|
| **Arquitetura** | Django 5.2 + Django REST Framework (DRF) |
| **Autenticação** | JWT via `simplejwt` |
| **Banco de Dados** | PostgreSQL (produção) / SQLite (desenvolvimento) |
| **Frontend** | Vue.js 3 (consome API via HTTP) |
| **IA** | Google Gemini API |
| **Relatórios** | CSV, Excel (.xlsx), PDF |
| **Isolamento** | Multi-tenant por `Empresa` |

### 1.3 Estrutura de Apps Django

```
projeto/
├── app/                    # Configurações globais
├── authentication/         # Login JWT, /me, troca de senha
├── accounts/              # Empresa e Usuário (modelo unificado)
├── ativos/                # Equipamentos, Localização, Planos de Manutenção
├── manutencao/            # Ordens de Serviço e Histórico
│   └── dashboards/        # KPIs (MTBF, MTTR, Disponibilidade)
├── telemetria/            # Sensores e Leituras de Telemetria
├── alertas/               # Alertas automáticos e manuais
├── exportacao/            # Exportadores (CSV, Excel, PDF)
└── gemini_api/            # Chat IA com Gemini
```

### 1.4 Tecnologias Utilizadas

- **Python 3.11+**, Django 5.2, DRF 3.16
- **simplejwt** — Autenticação JWT
- **drf-spectacular** — Swagger/OpenAPI automático
- **django-filter** — Filtros avançados
- **django-cors-headers** — Requisições cross-domain
- **google-generativeai** — Integração Gemini
- **WeasyPrint + ReportLab** — Geração de PDF
- **openpyxl** — Geração de Excel

---

## 2. MAPA DA ARQUITETURA ATUAL

### 2.1 Fluxo Geral da API

```
CLIENTE (Frontend)
        ↓
   HTTP/JWT
        ↓
   URL ROUTING (app/urls.py)
        ↓
   ViewSet (DRF)
        ├─→ Permission Check (permission_policies.py)
        ├─→ get_queryset() [isolamento multi-tenant]
        │
   Serializer (validação/transformação)
        ↓
   Signal Handlers (automação) ← IMPORTANTE
        │
   Service Layer (se existir)
        │
   ORM (Model layer)
        ↓
   Database
```

### 2.2 Fluxo Específico: Telemetria → Alertas → Ordens

Este é o pipeline **mais importante** do sistema:

```
┌─ Telemetria criada
│
├─→ Signal: telemetria/signals.py::checar_limites_telemetria()
│   ├─→ Verifica percentual do limite
│   ├─→ Define nível (baixo/médio/crítico)
│   ├─→ Cria ou atualiza Alerta (deduplicação incluída)
│
├─→ Signal: alertas/signals.py::vincular_ordem_servico_ao_alerta()
│   ├─→ Verifica se Alerta é novo
│   ├─→ Mapeia nível → prioridade
│   ├─→ Cria OrdemServico (tipo='corretiva')
│   └─→ Se O.S. já existe, escala prioridade
│
└─→ OrdemServico criada/atualizada
    └─→ Gestor e técnicos veem na interface
```

### 2.3 Fluxo Preditivo: Horímetro → Planos → Ordens

```
┌─ Equipamento.horimetro é atualizado
│
├─→ Signal: ativos/signals.py::verificar_planos_por_horimetro()
│   ├─→ Itera planos_manutencao
│   ├─→ Calcula: proximo_disparo = horimetro_ultima_os + intervalo_horas
│   ├─→ Se horimetro atual ≥ proximo_disparo:
│   │   ├─→ Checa duplicação
│   │   ├─→ Chama Gemini AI (se configurado) para descrição
│   │   ├─→ Cria OrdemServico (tipo='preditiva')
│   │   └─→ Atualiza horimetro_ultima_os do plano
│   │
└─→ OrdemServico preditiva criada
    └─→ Técnicos atribuídos veem e resolvem
```

### 2.4 Fluxo de Permissões

```
Request chega na ViewSet
        ↓
permission_classes verifica com PermissionPolicyFactory
        ↓
Factory retorna policy específica (gestor, tecnico, etc.)
        ↓
policy.can_access(user, method)
        ├─→ Verifica user.tipo_usuario
        ├─→ Verifica método HTTP
        ├─→ Retorna True/False
        ↓
Se OK: continua
Se não: retorna 403 Forbidden
```

### 2.5 Fluxo de Exportação

```
Usuário solicita export (GET /api/exportar/ordens-servico/{formato}/)
        ↓
View filtra OrdemServico (multi-tenant)
        ↓
ExportadorFactory.criar(formato)
        ├─→ factory._registro['csv'] → ExportadorCSV()
        ├─→ factory._registro['excel'] → ExportadorExcel()
        └─→ factory._registro['pdf'] → ExportadorPDF()
        ↓
Exportador.exportar(nome, titulo, colunas, linhas)
        ↓
HttpResponse com arquivo (Content-Disposition: attachment)
```

### 2.6 Fluxo de Construção de Prompts (IA)

```
Usuário solicita chat com IA
        ↓
build_chat_prompt(user, context, message)
        ├─→ Coleta contexto: equipamentos, ordens, alertas, telemetria
        ├─→ Instancia PromptBuilderConcreto()
        │
├─→ PromptDirector.montar_chat(builder, context, context_str, message)
│   ├─→ builder.reset()
│   ├─→ builder.com_contexto(context_str)
│   ├─→ builder.com_alertas(context['alert_summary'])
│   ├─→ builder.com_ordens(context['open_orders'])
│   ├─→ builder.com_telemetria(context['telemetry'])
│   ├─→ builder.com_pergunta(message)
│   └─→ builder.build() → Prompt
│
├─→ generate_content(system_instruction, user_prompt)
│   ├─→ Conecta com Gemini API
│   ├─→ Tenta múltiplos modelos (gemini-3.5-flash, gemini-2.5-flash, etc.)
│   └─→ Retorna resposta
│
└─→ Response retorna ao frontend
```

---

## 3. INVENTÁRIO DOS PADRÕES EXISTENTES

### Tabela de Status

| Padrão | Já Existe? | Localização | Está Correto? | Necessita Reestruturação? |
|--------|-----------|-------------|---------------|---------------------------|
| **Abstract Factory** | ✅ SIM | `exportacao/utils/exporter_factory.py` | ✅ SIM | ❌ NÃO |
| **Factory Method** | ✅ SIM | `accounts/permission_policies.py` | ✅ SIM | ❌ NÃO |
| **Builder** | ✅ SIM | `gemini_api/prompt_builder_pattern.py` | ✅ SIM | ❌ NÃO |
| **Singleton** | ❌ NÃO | — | — | ❌ NÃO APLICÁVEL |
| **Facade** | ⚠️ PARCIAL | `gemini_api/context_service.py` | ⚠️ INCOMPLETO | ⚠️ SIM |
| **Adapter** | ⚠️ PARCIAL | `gemini_api/cliente.py` | ⚠️ INCOMPLETO | ⚠️ SIM |
| **Composite** | ❌ NÃO | — | — | ❌ NÃO APLICÁVEL |
| **Decorator** | ❌ NÃO | — | — | ❌ NÃO APLICÁVEL |

---

## 4. ANÁLISE INDIVIDUAL DOS 8 PADRÕES

---

### 4.1 ABSTRACT FACTORY ✅ IMPLEMENTADO

#### Nome
- **Português**: Fábrica Abstrata
- **Inglês**: Abstract Factory

#### Categoria
**Criacional**

#### O que é
Padrão que fornece uma interface para criar **famílias de objetos relacionados** sem especificar suas classes concretas. Útil quando você tem múltiplas variantes de um conceito e quer que o cliente escolha qual família usar.

#### Objetivo
Garantir que objetos de diferentes variantes (CSV, Excel, PDF) sejam criados de forma **consistente** e que o cliente não precise conhecer as classes concretas.

#### Como está atualmente

**Localização**: `exportacao/utils/`

**Estrutura**:
```
exportacao/utils/
├── base_exporter.py         # Classe abstrata
├── exporter_factory.py      # Factory
├── csv_exporter.py          # Implementação
├── excel_exporter.py        # Implementação
├── pdf_exporter.py          # Implementação
└── __init__.py              # Registra as classes
```

**Código atual**:

```python
# base_exporter.py
class Exportador(ABC):
    @abstractmethod
    def exportar(self, nome: str, titulo: str, colunas: list, linhas: list) -> HttpResponse:
        pass

# exporter_factory.py
class ExportadorFactory:
    _registro = {}

    @classmethod
    def registrar(cls, formato: str, exportador_cls: type):
        cls._registro[formato] = exportador_cls

    @classmethod
    def criar(cls, formato: str) -> Exportador:
        exportador_cls = cls._registro.get(formato)
        if not exportador_cls:
            raise ValueError(f"Formato '{formato}' não suportado.")
        return exportador_cls()

# __init__.py
ExportadorFactory.registrar('csv', ExportadorCSV)
ExportadorFactory.registrar('excel', ExportadorExcel)
ExportadorFactory.registrar('pdf', ExportadorPDF)
```

**Uso**: 
```python
# exportacao/views.py
exportador = ExportadorFactory.criar(formato)
return exportador.exportar(nome, titulo, colunas, linhas)
```

#### Problema Identificado
**NENHUM** — Esta é uma implementação **correta e adequada**.

- A fábrica centraliza a criação
- Novos exportadores podem ser registrados sem alterar código existente
- O padrão resolve realmente um problema: evita blocos `if/elif` na seleção de exportadores
- A interface é consistente

#### Aplicação Proposta
**Manter como está**. A implementação está excelente.

#### Antes
```python
# SEM FACTORY (como seria sem o padrão)
def exportar_dados(formato, ...):
    if formato == 'csv':
        exporter = ExportadorCSV()
    elif formato == 'excel':
        exporter = ExportadorExcel()
    elif formato == 'pdf':
        exporter = ExportadorPDF()
    else:
        raise ValueError(...)
    return exporter.exportar(...)
```

#### Depois
```python
# COM FACTORY
exportador = ExportadorFactory.criar(formato)
return exportador.exportar(...)
# + novo formato é apenas ExportadorFactory.registrar('json', ExportadorJSON)
```

#### Por que Utilizar
- **Extensibilidade**: Adicionar novo formato não requer mudança em código existente
- **Centralização**: Todas as criações em um lugar
- **Segurança**: Falha explícita se formato inválido
- **Testabilidade**: Fácil mockar diferentes exportadores

#### Arquivos Envolvidos Atualmente
- `exportacao/utils/base_exporter.py`
- `exportacao/utils/exporter_factory.py`
- `exportacao/utils/csv_exporter.py`
- `exportacao/utils/excel_exporter.py`
- `exportacao/utils/pdf_exporter.py`
- `exportacao/utils/__init__.py`
- `exportacao/views.py` (uso)

#### Arquivos que Deverão ser Criados
**NENHUM** — Manter como está.

#### Arquivos que Deverão ser Modificados
**NENHUM** — Implementação está correta.

#### Classes Envolvidas
- `Exportador` (abstrata)
- `ExportadorCSV`, `ExportadorExcel`, `ExportadorPDF` (concretas)
- `ExportadorFactory` (fábrica)

#### Impacto nos Endpoints
**Nenhum** — Funciona completamente por trás dos endpoints.

```
GET /api/exportar/ordens-servico/csv/
GET /api/exportar/ordens-servico/excel/
GET /api/exportar/ordens-servico/pdf/
```

Todos continuam funcionando exatamente como estão.

#### Riscos
**Nenhum** — Padrão bem estabelecido e testado.

#### Testes Necessários
- Verificar que cada exportador retorna o formato correto
- Verificar que Factory.criar() levanta erro para formato inválido
- Testar com dados multi-tenant (filtragem preservada)

#### Decisão
```
✅ IMPLEMENTADO CORRETAMENTE
   Manter como está. Não modificar.
```

---

### 4.2 FACTORY METHOD ✅ IMPLEMENTADO

#### Nome
- **Português**: Método Fábrica
- **Inglês**: Factory Method

#### Categoria
**Criacional**

#### O que é
Padrão que define uma interface para criar um objeto, mas deixa as subclasses decidirem qual classe instanciar. Desacopla o criador da lógica de criação.

#### Objetivo
Centralizar e abstrair a lógica de criação de objetos que possuem múltiplas implementações.

#### Como está atualmente

**Localização**: `accounts/permission_policies.py`

**Estrutura**:
```
accounts/
├── permission_policies.py  # Factory + Policies
└── permissions.py          # Classes que usam a factory
```

**Código**:

```python
# permission_policies.py

from abc import ABC, abstractmethod

class BasePermissionPolicy(ABC):
    @abstractmethod
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        raise NotImplementedError

class GestorPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return user.tipo_usuario in ['gestor', 'admin']

class TecnicoPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return user.tipo_usuario == 'tecnico'

class GestorOrReadOnlyPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return user.tipo_usuario in ['gestor', 'admin']

class PermissionPolicyFactory:
    _policies = {
        'gestor': GestorPolicy(),
        'tecnico': TecnicoPolicy(),
        'gestor_or_readonly': GestorOrReadOnlyPolicy(),
        'authenticated_no_delete_for_tecnico': AuthenticatedNoDeleteForTecnicoPolicy(),
    }

    @classmethod
    def create(cls, policy_name: str):
        try:
            return cls._policies[policy_name]
        except KeyError as exc:
            raise ValueError(f"Política não registrada: {policy_name}") from exc

    @classmethod
    def register(cls, policy_name: str, policy: BasePermissionPolicy):
        cls._policies[policy_name] = policy
```

**Uso**:

```python
# permissions.py
class IsGestor(permissions.BasePermission):
    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('gestor')
        return policy.can_access(request.user, request.method)
```

#### Problema Identificado
**NENHUM** — Implementação correta e funcional.

- Factory centraliza a criação de policies
- Novas policies podem ser registradas sem alterar código existente
- Cada policy é responsável por sua própria lógica
- Pattern resolve um problema real: evitar instanciação direta em múltiplos lugares

#### Aplicação Proposta
**Manter como está**. Excelente implementação.

#### Antes
```python
# SEM FACTORY
class IsGestor(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.tipo_usuario in ['gestor', 'admin']

class IsTecnico(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.tipo_usuario == 'tecnico'

# Lógica repetida em múltiplos lugares
```

#### Depois
```python
# COM FACTORY
class IsGestor(permissions.BasePermission):
    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('gestor')
        return policy.can_access(request.user, request.method)

# Lógica centralizada, reutilizável, testável
```

#### Por que Utilizar
- **Reutilização**: Mesma policy em múltiplas permission classes
- **Centralização**: Lógica de validação em um lugar
- **Testabilidade**: Fácil testar policies isoladamente
- **Extensibilidade**: Novas policies sem alterar permissions.py

#### Arquivos Envolvidos Atualmente
- `accounts/permission_policies.py`
- `accounts/permissions.py` (uso)

#### Arquivos que Deverão ser Criados
**NENHUM**

#### Arquivos que Deverão ser Modificados
**NENHUM**

#### Classes Envolvidas
- `BasePermissionPolicy` (abstrata)
- `GestorPolicy`, `TecnicoPolicy`, `GestorOrReadOnlyPolicy`, `AuthenticatedNoDeleteForTecnicoPolicy` (concretas)
- `PermissionPolicyFactory` (factory)

#### Impacto nos Endpoints
**Nenhum** — Funciona por trás das permission_classes.

#### Riscos
**Nenhum**

#### Testes Necessários
- Verificar cada policy com diferentes tipos de usuário
- Verificar métodos HTTP permitidos/bloqueados
- Testar registro de novas policies

#### Decisão
```
✅ IMPLEMENTADO CORRETAMENTE
   Manter como está. Não modificar.
```

---

### 4.3 BUILDER ✅ IMPLEMENTADO

#### Nome
- **Português**: Construtor
- **Inglês**: Builder

#### Categoria
**Criacional**

#### O que é
Padrão que separa a construção de um objeto complexo de sua representação final, permitindo construção passo-a-passo.

#### Objetivo
Permitir construção incremental de objetos que possuem muitos componentes/partes.

#### Como está atualmente

**Localização**: `gemini_api/prompt_builder_pattern.py`

**Estrutura**:

```python
# prompt_builder_pattern.py

from abc import ABC, abstractmethod
from .prompt import Prompt

class PromptBuilder(ABC):
    @abstractmethod
    def com_contexto(self, context_str: str) -> 'PromptBuilder':
        pass
    @abstractmethod
    def com_alertas(self, alertas: list) -> 'PromptBuilder':
        pass
    @abstractmethod
    def com_ordens(self, ordens: list, titulo: str) -> 'PromptBuilder':
        pass
    @abstractmethod
    def com_telemetria(self, dados: list) -> 'PromptBuilder':
        pass
    @abstractmethod
    def com_financeiro(self, dados: list) -> 'PromptBuilder':
        pass
    @abstractmethod
    def com_instrucoes(self, texto: str) -> 'PromptBuilder':
        pass
    @abstractmethod
    def com_pergunta(self, texto: str) -> 'PromptBuilder':
        pass
    @abstractmethod
    def build(self) -> Prompt:
        pass
    @abstractmethod
    def reset(self) -> None:
        pass

class PromptBuilderConcreto(PromptBuilder):
    def __init__(self):
        self._blocos = []
        self._max_linhas = 5

    def reset(self):
        self._blocos = []

    def com_contexto(self, context_str: str) -> 'PromptBuilder':
        if context_str:
            self._blocos.append(context_str)
        return self

    def com_alertas(self, alertas: list) -> 'PromptBuilder':
        if alertas:
            linhas = [f"- {linha}" if not linha.startswith("-") else linha for linha in alertas]
            truncadas = self._truncar(linhas, self._max_linhas)
            if truncadas:
                self._blocos.append("\nALERTAS RELEVANTES:\n" + "\n".join(truncadas))
        return self

    def com_ordens(self, ordens: list, titulo: str) -> 'PromptBuilder':
        if ordens:
            # ... similar logic
            self._blocos.append(f"\n{titulo}:\n" + "\n".join(truncadas))
        return self

    # ... outros métodos ...

    def build(self) -> Prompt:
        resultado = "\n".join(self._blocos)
        return Prompt(resultado)
```

**Uso** (via Director pattern):

```python
# prompt_director.py
class PromptDirector:
    @staticmethod
    def montar_chat(builder: PromptBuilder, context: dict, context_str: str, message: str) -> Prompt:
        builder.reset()
        builder.com_contexto(context_str)
        builder.com_alertas(context.get('alert_summary', []))
        builder.com_ordens(context.get('open_orders'), "ORDENS EM ABERTO")
        builder.com_telemetria(context.get('telemetry', []))
        builder.com_pergunta(message)
        return builder.build()
```

#### Problema Identificado
**NENHUM** — Implementação correta e elegante.

- Builder permite construção incremental de prompts complexos
- Cada `com_*` retorna `self` para encadeamento (fluent interface)
- Reset permite reutilização
- Truncagem de dados integrada

#### Aplicação Proposta
**Manter como está**. Funciona muito bem.

#### Por que Utilizar
- **Legibilidade**: `builder.com_contexto(...).com_alertas(...).com_ordens(...).build()`
- **Flexibilidade**: Cada "parte" é opcional
- **Reutilização**: Mesmo builder para diferentes tipos de prompts
- **Manutenibilidade**: Fácil adicionar novos componentes

#### Arquivos Envolvidos Atualmente
- `gemini_api/prompt_builder_pattern.py` (builder concreto)
- `gemini_api/prompt.py` (objeto final)
- `gemini_api/prompt_director.py` (diretor - opcional mas presente)
- `gemini_api/prompt_builder.py` (uso)

#### Impacto nos Endpoints
**Nenhum** — Funciona internamente no contexto da IA.

Endpoints `/api/gemini/chat/` continuam funcionando normalmente.

#### Riscos
**Nenhum**

#### Testes Necessários
- Verificar que cada componente é construído corretamente
- Verificar que omitir componentes funciona
- Testar truncagem de dados
- Verificar encadeamento (fluent interface)

#### Decisão
```
✅ IMPLEMENTADO CORRETAMENTE
   Manter como está. Não modificar.
```

---

### 4.4 SINGLETON ❌ NÃO APLICÁVEL

#### Nome
- **Português**: Singleton
- **Inglês**: Singleton

#### Categoria
**Criacional**

#### O que é
Padrão que garante que uma classe possua **uma única instância** em todo o programa e fornece um ponto de acesso global a ela.

#### Objetivo
Centralizar acesso a recursos compartilhados únicos (logger, configuração, pool de conexões).

#### Como está atualmente
**NÃO IMPLEMENTADO** de forma explícita.

#### Problema Identificado
**NÃO HÁ CASO DE USO SEGURO OU JUSTIFICÁVEL** neste projeto.

#### Análise Detalhada

**Candidatos iniciais** que poderiam parecer Singleton:

1. **PermissionPolicyFactory._policies** — Já é singleton-like (dicionário de classe compartilhado)
   - ❌ Não precisa ser explícito; funciona bem como está
   - ❌ Django já gerencia o ciclo de vida da classe

2. **ExportadorFactory._registro** — Mesmo caso
   - ❌ Já é singleton-like; não precisa ser explícito

3. **PromptConfig.objects** — Queryset do ORM
   - ❌ Django ORM já gerencia instâncias corretamente
   - ❌ Implementar Singleton causaria problemas com multi-worker

4. **Gemini Client** — Integração com API externa
   - ⚠️ **PROBLEMA**: Em ambiente multi-worker (production), um Singleton compartilhado causaria:
     - Contenção de thread
     - Vazamento de conexões
     - Problemas de serialização
   - ✅ **SOLUÇÃO ATUAL** é melhor: `get_gemini_client()` cria instâncias conforme necessário

#### Por que NÃO Usar Singleton Aqui

**Em Django com múltiplos workers/processos**:

```
Cenário RUIM com Singleton:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Worker 1       │  │  Worker 2       │  │  Worker 3       │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ↓
                    Instância ÚNICA compartilhada
                    (PROBLEMA: race conditions!)
```

```
Cenário BOM com Factory:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Worker 1       │  │  Worker 2       │  │  Worker 3       │
├─ Instância A   │  ├─ Instância B   │  ├─ Instância C   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
(Cada worker sua própria instância — thread-safe, sem compartilhamento perigoso)
```

#### Componentes que Já São "Singleton-like" Naturalmente

1. **PermissionPolicyFactory._policies**
   ```python
   _policies = {
       'gestor': GestorPolicy(),  # ← Uma instância única por policy
       'tecnico': TecnicoPolicy(),
       ...
   }
   ```
   - ✅ É singleton-like porque é atributo de classe
   - ✅ Funciona perfeitamente
   - ❌ Não precisa de padrão explícito

2. **Django ORM Model classes**
   - Django já cuida de manter apenas uma classe por model
   - Não precisa de Singleton

3. **Django Settings object**
   - `from django.conf import settings`
   - ✅ É efetivamente Singleton (sem precisar de padrão)

#### Aplicação Proposta
**NENHUMA** — Não implementar Singleton.

#### Decisão
```
❌ NÃO APLICÁVEL
   Caso de uso seguro não existe no contexto desta aplicação Django com múltiplos workers.
   Padrões atuais (Factory, classe com atributos de classe) funcionam melhor.
   NÃO criar Singleton artificialmente.
```

---

### 4.5 FACADE ⚠️ PARCIALMENTE IMPLEMENTADO

#### Nome
- **Português**: Fachada
- **Inglês**: Facade

#### Categoria
**Estrutural**

#### O que é
Padrão que fornece uma **interface unificada** para um conjunto de interfaces em um subsistema. Simplifica o uso de componentes complexos.

#### Objetivo
Reduzir complexidade ao encapsular múltiplos componentes por trás de uma única interface.

#### Como está atualmente

**Localização**: `gemini_api/context_service.py`

**Código**:

```python
def build_alert_summary(alerts, limit=5):
    summary = []
    for alerta in alerts[:limit]:
        summary.append(f"- [{alerta.nivel.upper()}] ...")
    return summary

def build_order_summary(orders, limit=5):
    summary = []
    for ordem in orders[:limit]:
        summary.append(f"- #{ordem.id} ...")
    return summary

def build_equipment_kpi_summary(user, max_equip=5):
    equipamentos = get_user_equipment_queryset(user)
    summary = []
    for equipamento in equipamentos[:max_equip]:
        kpi = KpiService.calcular_kpi(equipamento, os_base)
        summary.append(...)
    return summary

def get_financial_summary():
    # Coleta dados financeiros
    ...
```

#### Problema Identificado

A implementação é **parcial e desorganizada**:

1. **Sem interface unificada**: Funções soltas, sem classe façade
2. **Responsabilidades misturadas**:
   - `get_open_orders()` — busca ORM
   - `build_alert_summary()` — formatação
   - `get_financial_summary()` — cálculos financeiros
3. **Sem encapsulamento**: Código chamador precisa conhecer detalhes
4. **Difícil de testar**: Múltiplas dependências em cada função

#### Exemplo de Uso Atual (COMPLEXO)

```python
# gemini_api/views.py
def post(self, request):
    user = request.user
    
    # Coleta manual de múltiplas fontes
    context = {
        'company_name': user.empresa.nome,
        'total_equipment': Equipamento.objects.filter(empresa=user.empresa).count(),
        'active_equipment': Equipamento.objects.filter(empresa=user.empresa, status='ativo').count(),
        'open_orders': get_open_orders(user),  # Chama helper
        'unassigned_orders': get_unassigned_orders(user),  # Chama helper
        'alert_summary': build_alert_summary(get_active_alerts(user)),  # Encadeamento complexo
        'open_order_summary': build_order_summary(get_open_orders(user)),
        'equipment_kpis': build_equipment_kpi_summary(user),
        'telemetry': get_recent_telemetry(user),
        'financial_summary': get_financial_summary(),
    }
    
    # Monta prompt manualmente
    prompt = build_chat_prompt(user, context, message)
    ...
```

**Problema**: Muito acoplamento entre view e serviço.

#### Aplicação Proposta

**Criar uma classe `ContextFacade`** que:

1. **Centraliza a coleta de contexto**
2. **Oferece método único para diferentes tipos de contexto**
3. **Encapsula detalhes de implementação**
4. **Reutilizável em múltiplos endpoints**

**Novo Design**:

```python
# PROPOSTO: gemini_api/context_facade.py

class ContextFacade:
    """Façade que centraliza a coleta de contexto para IA."""
    
    def __init__(self, user):
        self.user = user
    
    def build_chat_context(self):
        """Coleta contexto para chat genérico."""
        return {
            'company_name': self._get_company_name(),
            'total_equipment': self._count_equipment(),
            'active_equipment': self._count_equipment(status='ativo'),
            'maintenance_equipment': self._count_equipment(status='manutencao'),
            'inactive_equipment': self._count_equipment(status='inativo'),
            'open_orders': self._get_open_orders(),
            'unassigned_orders': self._get_unassigned_orders(),
            'alert_summary': self._build_alert_summary(),
            'open_order_summary': self._build_order_summary(),
            'equipment_kpis': self._build_equipment_kpi_summary(),
            'telemetry': self._get_recent_telemetry(),
        }
    
    def build_os_analysis_context(self):
        """Coleta contexto para análise de ordens."""
        return {
            'company_name': self._get_company_name(),
            'assigned_orders': self._get_assigned_orders(),
            'unassigned_orders': self._get_unassigned_orders(),
            'assigned_order_summary': self._build_order_summary(self._get_assigned_orders()),
            'unassigned_order_summary': self._build_order_summary(self._get_unassigned_orders()),
        }
    
    def build_financial_context(self):
        """Coleta contexto financeiro."""
        return {
            'company_name': self._get_company_name(),
            'financial_summary': self._build_financial_summary(),
        }
    
    # Métodos privados (implementação encapsulada)
    def _get_company_name(self):
        return self.user.empresa.nome if self.user.empresa else 'Admin'
    
    def _count_equipment(self, status=None):
        qs = self._get_equipment_queryset()
        if status:
            qs = qs.filter(status=status)
        return qs.count()
    
    # ... outros métodos privados ...
```

**Novo Uso (SIMPLES)**:

```python
# gemini_api/views.py
def post(self, request):
    facade = ContextFacade(request.user)
    context = facade.build_chat_context()  # ← Uma linha!
    prompt = build_chat_prompt(request.user, context, message)
    ...
```

#### Antes
```
View
 ├── Coleta equipamentos manualmente
 ├── Coleta ordens manualmente
 ├── Chama múltiplas funções de construção
 ├── Entra contexto em dicionário
 ├── Monta prompt
 └── Envia para IA
(muito acoplamento, difícil de testar)
```

#### Depois
```
View
 ├── ContextFacade.build_chat_context()  ← Uma chamada
 └── (tudo é interno à façade)
(simplificado, desacoplado)
```

#### Por que Utilizar
- **Simplificação**: Interface unificada em vez de múltiplas funções
- **Manutenibilidade**: Mudanças no contexto ficam em um lugar
- **Testabilidade**: Fácil mockar a façade
- **Reutilização**: Diferentes views podem usar `build_os_analysis_context()` sem duplicação

#### Arquivos Envolvidos Atualmente
- `gemini_api/context_service.py` (funções soltas)
- `gemini_api/views.py` (uso complexo)
- `gemini_api/prompt_builder.py` (construção de prompts)

#### Arquivos que Deverão ser Criados
- **`gemini_api/context_facade.py`** — Nova classe façade (sugerido)

#### Arquivos que Deverão ser Modificados
- `gemini_api/views.py` — Usar façade em vez de chamar funções diretamente
- `gemini_api/context_service.py` — (opcional) mover funções auxiliares para dentro da façade

#### Classes Envolvidas
- Proposta: `ContextFacade` (classe façade)
- Afetadas: Views do gemini_api

#### Impacto nos Endpoints
**Nenhum** — Endpoints continuam funcionando normalmente:
```
POST /api/gemini/chat/
POST /api/gemini/os-analysis/
POST /api/gemini/unassigned-orders/
POST /api/gemini/finance/
```

#### Riscos
- **Baixo**: Refatoração é interna
- Endpoints não são alterados
- Comportamento funcional não muda

#### Testes Necessários
- Verificar que façade retorna contexto correto
- Verificar multi-tenant isolation dentro da façade
- Testar cada contexto diferente (chat, os_analysis, finance)

#### Decisão
```
⚠️ REESTRUTURAÇÃO RECOMENDADA
   Criar ContextFacade para centralizar coleta de contexto.
   Isso simplificará views e melhorará testabilidade.
   Mudança interna — não afeta endpoints.
   Risco baixo.
```

---

### 4.6 ADAPTER ⚠️ PARCIALMENTE IMPLEMENTADO

#### Nome
- **Português**: Adaptador
- **Inglês**: Adapter

#### Categoria
**Estrutural**

#### O que é
Padrão que converte a **interface de um objeto** para outra interface que o cliente espera. Permite que objetos incompatíveis colaborem.

#### Objetivo
Proteger o restante do sistema contra mudanças em APIs externas, oferecendo uma interface interna consistente.

#### Como está atualmente

**Localização**: `gemini_api/cliente.py`

**Código**:

```python
from google import genai

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def generate_content(system_instruction, user_prompt, history=None, model_candidates=None, temperature=0.4):
    client = get_gemini_client()
    if not client:
        raise RuntimeError("Chave GEMINI_API_KEY não configurada.")
    
    # Monta history no formato esperado pela API
    contents = []
    if history:
        for item in history:
            role = "user" if item.get("role") == "user" else "model"
            contents.append(types.Content(role=role, parts=[...]))
    
    # Tenta múltiplos modelos
    for model_name in model_candidates:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            return response.text, model_name
        except Exception as e:
            if recoverable(e):
                continue
            raise
    
    raise RuntimeError(...)
```

#### Problema Identificado

A implementação é **parcial e sem interface clara**:

1. **Sem classe adaptadora**: Funções soltas, não classes
2. **Detalhes da API externa vazam**: Código chamador conhece `types.Content`, `model_name`, etc.
3. **Sem contrato interno**: Se API externa muda, necessário ajustar múltiplos lugares
4. **Difícil de testar**: Direto acoplado à Google API

#### Exemplo de Uso Atual (ACOPLADO)

```python
# gemini_api/views.py
def post(self, request):
    response_text, model_name = generate_content(
        system_instruction=system_instruction,
        user_prompt=user_prompt,
        history=history,
        model_candidates=[...],  # Conhece detalhes externos
        temperature=0.4,
    )
    ...
```

**Problema**: Se Google mudar a API, precisa alterar código aqui.

#### Aplicação Proposta

**Criar uma classe `GeminiAdapter`** que:

1. **Encapsula completamente a API Google**
2. **Oferece interface interna consistente**
3. **Protege o restante do código contra mudanças externas**

**Novo Design**:

```python
# PROPOSTO: gemini_api/adapters.py

from abc import ABC, abstractmethod
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

class IAAdapter(ABC):
    """Interface interna para provedores de IA."""
    
    @abstractmethod
    def gerar_conteudo(self, instrucao_sistema: str, pergunta_usuario: str, 
                       historico: list = None, temperatura: float = 0.4) -> tuple:
        """
        Gera conteúdo de IA.
        
        Retorna: (texto_resposta, nome_modelo_usado)
        """
        pass

class GeminiAdapter(IAAdapter):
    """Adaptador para Google Gemini API."""
    
    DEFAULT_MODELS = [
        "gemini-3.5-flash",
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ]
    
    def __init__(self):
        self.client = self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa cliente Gemini ou retorna None."""
        load_dotenv(override=True)
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.strip() == "":
            return None
        try:
            return genai.Client(api_key=api_key)
        except Exception:
            return None
    
    def is_available(self) -> bool:
        """Retorna True se IA está disponível."""
        return self.client is not None
    
    def gerar_conteudo(self, instrucao_sistema: str, pergunta_usuario: str, 
                       historico: list = None, temperatura: float = 0.4) -> tuple:
        """
        Gera conteúdo usando Gemini.
        
        Args:
            instrucao_sistema: Instrução do sistema
            pergunta_usuario: Pergunta/prompt do usuário
            historico: Lista de mensagens anteriores [{'role': 'user'/'model', 'text': '...'}]
            temperatura: Controle de criatividade (0.0-1.0)
        
        Returns:
            (texto_resposta, nome_modelo)
        
        Raises:
            RuntimeError: Se IA indisponível ou todos os modelos falharem
        """
        if not self.is_available():
            raise RuntimeError("Chave GEMINI_API_KEY não configurada.")
        
        # Converte histórico para formato Gemini (detalhes de adaptação encapsulados aqui)
        contents = self._build_contents(historico, pergunta_usuario)
        
        # Tenta modelos em ordem
        last_error = None
        for model_name in self.DEFAULT_MODELS:
            try:
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=instrucao_sistema,
                        temperature=temperatura,
                    ),
                )
                return response.text, model_name
            except Exception as e:
                if self._is_recoverable_error(e):
                    last_error = e
                    continue
                raise
        
        raise RuntimeError(f"Todos os modelos Gemini falharam: {last_error}")
    
    def _build_contents(self, historico, pergunta_usuario):
        """Converte histórico e pergunta para formato Gemini."""
        contents = []
        
        if historico:
            for item in historico:
                role = "user" if item.get("role") == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=item.get("text", ""))]
                ))
        
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=pergunta_usuario)]
        ))
        
        return contents
    
    def _is_recoverable_error(self, error: Exception) -> bool:
        """Determina se erro é recuperável (tentar outro modelo)."""
        err_str = str(error)
        recoverable_indicators = [
            "503", "UNAVAILABLE", "ResourceExhausted", "429",
            "404", "NOT_FOUND", "not found"
        ]
        return any(indicator in err_str for indicator in recoverable_indicators)


# Singleton-like factory para o adapter
_adapter_instance = None

def get_ia_adapter() -> IAAdapter:
    """Retorna instância do adaptador (lazy-loaded)."""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = GeminiAdapter()
    return _adapter_instance
```

**Novo Uso (SIMPLES E DESACOPLADO)**:

```python
# gemini_api/views.py
def post(self, request):
    adapter = get_ia_adapter()
    
    if not adapter.is_available():
        return Response({'error': 'IA indisponível'}, status=503)
    
    response_text, model_used = adapter.gerar_conteudo(
        instrucao_sistema=system_instruction,
        pergunta_usuario=user_prompt,
        historico=history,
        temperatura=0.4,
    )
    
    return Response({
        'resposta': response_text,
        'modelo': model_used,
    })
```

#### Antes
```
View conhece:
- genai.Client
- types.Content, types.Part
- model_candidates
- Tratamento de erro específico
- Tentativa de múltiplos modelos
- Conversão de histórico

Se API muda → Precisa alterar aqui
```

#### Depois
```
View conhece apenas:
- get_ia_adapter()
- adapter.gerar_conteudo(...)

Todos os detalhes Google encapsulados no adapter.
Se API muda → Alterar apenas no adapter
```

#### Por que Utilizar
- **Isolamento**: Detalhes Google não vazam para o código
- **Manutenibilidade**: Se Google muda API, alterar em um lugar
- **Testabilidade**: Fácil mockar adapter com interface interna
- **Flexibilidade**: Trocar por outro provider (OpenAI, Anthropic) sem alterar código

#### Arquivos Envolvidos Atualmente
- `gemini_api/cliente.py` (funções soltas)
- `gemini_api/views.py` (uso)
- `gemini_api/context_service.py` (uso)
- `telemetria/signals.py` (uso)
- `ativos/signals.py` (uso)

#### Arquivos que Deverão ser Criados
- **`gemini_api/adapters.py`** — Novo arquivo com GeminiAdapter

#### Arquivos que Deverão ser Modificados
- `gemini_api/cliente.py` (opcional: manter para compatibilidade, importar do adapter)
- `gemini_api/views.py` — Usar adapter
- `gemini_api/context_service.py` — Usar adapter
- `telemetria/signals.py` — Usar adapter
- `ativos/signals.py` — Usar adapter

#### Classes Envolvidas
- Proposta: `IAAdapter` (interface abstrata)
- Proposta: `GeminiAdapter` (implementação)
- Afetadas: Views, signals, context_service

#### Impacto nos Endpoints
**Nenhum** — Endpoints continuam iguais:
```
POST /api/gemini/chat/
POST /api/gemini/os-analysis/
...
```

#### Riscos
- **Baixo**: Encapsulação apenas, sem mudança de lógica
- Pode manter `cliente.py` para compatibilidade retroativa

#### Testes Necessários
- Mockar `GeminiAdapter` para testar views sem chamar API real
- Verificar tratamento de erros recuperáveis/não-recuperáveis
- Testar que histórico é formatado corretamente

#### Decisão
```
⚠️ REESTRUTURAÇÃO RECOMENDADA
   Criar GeminiAdapter para encapsular API externa.
   Melhora testabilidade e manutenibilidade.
   Mudança interna — não afeta endpoints.
   Risco baixo.
```

---

### 4.7 COMPOSITE ❌ NÃO APLICÁVEL

#### Nome
- **Português**: Composto
- **Inglês**: Composite

#### Categoria
**Estrutural**

#### O que é
Padrão que permite compor objetos em **estruturas de árvore** para representar hierarquias **parte-todo**. Clientes podem tratar objetos individuais e composições de forma uniforme.

#### Objetivo
Simplificar o trabalho com estruturas hierárquicas tratando partes e composições como a mesma interface.

#### Como está atualmente
**NÃO IMPLEMENTADO** — Sem estruturas hierárquicas claras.

#### Análise Detalhada

**Candidatos analisados**:

1. **EquipamentoLocalizacao** — Localização de equipamentos
   ```python
   class EquipamentoLocalizacao(models.Model):
       equipamento = models.OneToOneField(Equipamento)
       setor = models.CharField(max_length=100)
   ```
   - ❌ É apenas um relacionamento 1:1, não é hierárquico
   - ❌ Não tem composição de múltiplas localizações
   - ❌ Não tem estrutura de árvore

2. **PlanoManutencao → Equipamento** — Planos em equipamentos
   ```python
   class PlanoManutencao(models.Model):
       equipamento = models.ForeignKey(Equipamento)
       # ...
   ```
   - ❌ Relacionamento 1:N plano, não é Composite
   - ❌ Planos não contêm outros planos
   - ❌ Não é uma hierarquia

3. **Alertas por Equipamento** — Alertas agrupados
   ```python
   class Alerta(models.Model):
       equipamento = models.ForeignKey(Equipamento)
       # ...
   ```
   - ❌ Alertas não são composições
   - ❌ Equipamento não é um Container de alertas
   - ❌ Sem tratamento uniforme necessário

4. **Manutencao → HistoricoManutencao** — Histórico de manutenções
   ```python
   class HistoricoManutencao(models.Model):
       ordem_servico = models.OneToOneField(OrdemServico)
       # ...
   ```
   - ❌ Relacionamento 1:1, não é Composite
   - ❌ Sem hierarquia aninhada

#### Por que NÃO Usar Composite Aqui

1. **Sem estrutura recursiva**: Nenhuma entidade contém outras entidades do mesmo tipo

2. **Sem necessidade de tratamento uniforme**:
   ```python
   # Para ser Composite, seria algo tipo:
   class Componente(ABC):
       @abstractmethod
       def contar_alertas(self) -> int:
           pass
   
   class EquipamentoFolha(Componente):
       def contar_alertas(self) -> int:
           return self.alertas.count()
   
   class GrupoEquipamentos(Componente):
       componentes: List[Componente]
       def contar_alertas(self) -> int:
           return sum(c.contar_alertas() for c in self.componentes)
   
   # Mas isso não é necessário neste projeto
   ```

3. **Django ORM não é adequado para Composite**: A implementação em banco relacional é complexa

4. **Casos de uso reais não existem**:
   - Não há necessidade de "grupo de equipamentos" que seja tratado como um equipamento
   - Não há hierarquias de setores que precisem de tratamento uniforme
   - Não há agrupamento recursivo

#### Aplicação Proposta
**NENHUMA** — Não implementar Composite.

Se no futuro houver necessidade de estruturas hierárquicas (ex: árvore de departamentos, setores dentro de setores), considerar Composite nesse momento.

#### Decisão
```
❌ NÃO APLICÁVEL
   Nenhuma estrutura hierárquica recursiva identificada.
   Nenhum caso de uso que se beneficiaria de Composite.
   NÃO criar artificialmente.
```

---

### 4.8 DECORATOR ❌ NÃO APLICÁVEL

#### Nome
- **Português**: Decorador
- **Inglês**: Decorator

#### Categoria
**Estrutural**

#### O que é
Padrão que permite **adicionar comportamentos** a objetos dinamicamente (em tempo de execução), sem alterar suas classes originais. Implementa composição de objetos com delegação.

#### Objetivo
Adicionar responsabilidades a objetos de forma flexível, sem usar subclasses.

#### Como está atualmente
**NÃO IMPLEMENTADO** de forma explícita como padrão estrutural.

**Nota importante**: Python tem `@decorator` (função que envolve função), mas isso é **diferente** do **padrão estrutural Decorator**.

#### Análise Detalhada

**Candidatos analisados**:

1. **@decorator Python para autorização**
   ```python
   @receiver(post_save, sender=Alerta)
   def vincular_ordem_servico_ao_alerta(sender, instance, created, **kwargs):
       # ...
   ```
   - ⚠️ É um `@receiver` (padrão Observer), não padrão Decorator
   - ❌ Não adiciona comportamento a um objeto específico
   - ❌ É um hook automático, não composição

2. **Logging/Auditoria** — Poderia usar Decorator?
   ```python
   # Seria algo tipo:
   class ServicoComLog:
       def __init__(self, servico: Servico):
           self.servico = servico
       
       def fazer_algo(self):
           logger.info("Iniciando...")
           resultado = self.servico.fazer_algo()
           logger.info("Finalizado")
           return resultado
   ```
   - ⚠️ **Não há serviços explícitos** para decorar
   - ❌ Código atual não estrutura com camada de serviços clara
   - ❌ ViewSets chamam diretamente ORM, não há "serviço" que possa ser decorado

3. **Cache** — Poderia usar Decorator?
   ```python
   class RepositorioComCache:
       def __init__(self, repo: Repositorio):
           self.repo = repo
           self.cache = {}
       
       def get_equipamentos(self, empresa_id):
           if empresa_id in self.cache:
               return self.cache[empresa_id]
           result = self.repo.get_equipamentos(empresa_id)
           self.cache[empresa_id] = result
           return result
   ```
   - ⚠️ **Não há camada de repositório** explícita
   - ❌ ORM é usado diretamente em ViewSets via `get_queryset()`
   - ❌ Cache não seria benefício (Django ORM já tem caching de queries)

4. **Permissões** — Poderia usar Decorator?
   ```python
   # Seria algo tipo:
   class PermissaoDecorator:
       def __init__(self, servico):
           self.servico = servico
       
       def executar(self, user):
           if not user.has_permission(...):
               raise PermissionDenied()
           return self.servico.executar()
   ```
   - ⚠️ DRF já trata isso com `permission_classes`
   - ❌ Forçar Decorator aqui seria duplicação
   - ❌ Padrão DRF é mais adequado

#### Por que NÃO Usar Decorator Aqui

1. **Sem serviços encapsulados**: Arquitetura atual (ViewSet → ORM) não tem camada de serviço para decorar

2. **Django DRF resolve necessidades de forma melhor**:
   - Permissões → `permission_classes`
   - Validação → Serializers
   - Hooks → `perform_create()`, `perform_update()`
   - Signals → `@receiver`

3. **Introduziria complexidade sem benefício**:
   ```python
   # RUIM: Forçar Decorator
   class GeminiComLogDecorator:
       def __init__(self, gemini_adapter):
           self.adapter = gemini_adapter
       
       def gerar_conteudo(self, ...):
           logger.info("Chamando Gemini...")
           resultado = self.adapter.gerar_conteudo(...)
           logger.info(f"Resultado: {resultado}")
           return resultado
   
   # Isso é só uma wrapper desnecessária
   ```

4. **Casos de uso reais não existem**:
   - Não há necessidade de adicionar comportamentos dinamicamente
   - Logging existente em celery tasks ou signals é suficiente
   - Não há necessidade de composição de comportamentos

#### Aplicação Proposta
**NENHUMA** — Não implementar Decorator.

Se no futuro houver:
- Camada de serviços explícita
- Necessidade de adicionar comportamentos dinamicamente (ex: múltiplas camadas de cache, logging condicional)
- Então considerar Decorator nesse momento

Por enquanto, padrões Django existentes (Signals, permission_classes, Serializers) são mais apropriados.

#### Decisão
```
❌ NÃO APLICÁVEL
   Arquitetura não possui camada de serviço encapsulada.
   Padrões Django (permission_classes, Serializers, Signals) são mais adequados.
   NÃO criar Decorator artificialmente.
```

---

## 5. INTERAÇÃO ENTRE PADRÕES

### Combinações Naturais Identificadas

#### Combinação 1: Builder + Director
**Implementado em**: `gemini_api/`

```
PromptDirector (quem orquestra)
        ↓
PromptBuilderConcreto (quem constrói)
        ↓
Prompt (resultado)
```

✅ Funciona bem, sem mudanças necessárias.

#### Combinação 2: Factory Methods + Policies
**Implementado em**: `accounts/`

```
PermissionPolicyFactory (factory)
        ↓
BasePermissionPolicy (interface)
        ├─ GestorPolicy
        ├─ TecnicoPolicy
        └─ ... outras policies
```

✅ Funciona bem, sem mudanças necessárias.

#### Combinação 3: Abstract Factory + Registration Pattern
**Implementado em**: `exportacao/`

```
ExportadorFactory (factory)
        ↓
Exportador (interface)
├─ ExportadorCSV
├─ ExportadorExcel
└─ ExportadorPDF
```

✅ Funciona bem, sem mudanças necessárias.

#### Combinação 4: Adapter + Facade (PROPOSTA)
**Proposta em**: `gemini_api/`

```
ContextFacade (coleta)
        ↓
GeminiAdapter (converte API)
        ↓
Google Gemini API
```

Essa seria uma boa combinação a implementar.

---

## 6. PLANO DE IMPLEMENTAÇÃO

### Ordem Recomendada

Após aprovação para implementação, seguir esta ordem:

#### Etapa 1: GeminiAdapter (Adapter Pattern)
- Criar `gemini_api/adapters.py`
- Encapsular Google Gemini API
- Manter `cliente.py` por compatibilidade

**Motivo**: Base para outras integrações de IA

#### Etapa 2: ContextFacade (Facade Pattern)
- Criar `gemini_api/context_facade.py`
- Centralizar coleta de contexto
- Usa GeminiAdapter da Etapa 1

**Motivo**: Depende de adapter estar pronto

#### Etapa 3: Atualizar Views
- `gemini_api/views.py` — Usar ContextFacade
- `gemini_api/context_service.py` — (opcional) refatorar

**Motivo**: Usa Facade da Etapa 2

#### Etapa 4: Testar
- Testes unitários de Adapter e Facade
- Testes de integração dos endpoints
- Verificar compatibilidade multi-tenant

---

## 7. RISCO DE REGRESSÃO

### Pontos Críticos a Monitorar

#### 1. Isolamento Multi-Tenant
**Verificar**: Cada camada mantém filtro por `empresa`

```
✓ get_queryset()
✓ context_facade._get_equipment_queryset()
✓ Alertas/Ordens filtradas por empresa
```

#### 2. Endpoints Críticos (NÃO ALTERAR)
```
POST   /api/auth/token/              ← Autenticação
GET    /api/auth/me/                 ← Perfil usuário
POST   /api/gemini/chat/             ← Chat IA
GET    /api/exportar/ordens-servico/ ← Exportação
```

Esses endpoints devem continuar funcionando **identicamente**.

#### 3. Signals (NÃO QUEBRAR)
```
telemetria.signals → Alerta criado
alertas.signals → OrdemServico criada
ativos.signals → Preditiva gerada
```

Se mudar acesso a Gemini, garantir que `ativos/signals.py` continua funcionando.

#### 4. Permissões (NÃO ALTERAR)
```
permission_policies.py → Todas as policies funcionam
IsGestor, IsGestorOrReadOnly, etc → Sem quebra
```

#### 5. Database Migrations
- ✅ Nenhuma migração necessária (sem mudanças de schema)

#### 6. Imports Circulares
- Atentar com novo `adapters.py` — evitar import cíclico

---

## 8. ESTRATÉGIA DE TESTES

### Testes Existentes
```
python manage.py test
```

Executar antes e depois de mudanças.

### Testes Específicos para Novos Padrões

#### Adapter (GeminiAdapter)
```python
def test_adapter_is_available():
    adapter = GeminiAdapter()
    assert isinstance(adapter.is_available(), bool)

def test_adapter_gerar_conteudo():
    adapter = GeminiAdapter()
    if adapter.is_available():
        texto, modelo = adapter.gerar_conteudo(
            "Você é assistente",
            "Qual é 2+2?",
            historia=None,
            temperatura=0.4
        )
        assert isinstance(texto, str)
        assert isinstance(modelo, str)

def test_adapter_error_handling():
    adapter = GeminiAdapter()
    with pytest.raises(RuntimeError):
        adapter.gerar_conteudo("", "", None, 0.4)  # Sem API key
```

#### Facade (ContextFacade)
```python
def test_facade_build_chat_context():
    user = criar_usuario_teste()
    facade = ContextFacade(user)
    context = facade.build_chat_context()
    
    assert 'company_name' in context
    assert 'open_orders' in context
    assert 'alert_summary' in context
    assert 'telemetry' in context

def test_facade_multi_tenant():
    user1 = criar_usuario(empresa=empresa1)
    user2 = criar_usuario(empresa=empresa2)
    
    facade1 = ContextFacade(user1)
    facade2 = ContextFacade(user2)
    
    context1 = facade1.build_chat_context()
    context2 = facade2.build_chat_context()
    
    # Contextos devem ser diferentes
    assert context1 != context2
```

#### Endpoints (Integração)
```python
def test_post_gemini_chat_endpoint():
    client = APIClient()
    user = criar_usuario_teste()
    token = obter_token_jwt(user)
    
    response = client.post(
        '/api/gemini/chat/',
        {'message': 'Qual é o status das ordens abertas?'},
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    
    assert response.status_code == 200
    assert 'resposta' in response.data

def test_exportar_ordens_endpoint():
    client = APIClient()
    user = criar_usuario_teste()
    token = obter_token_jwt(user)
    
    response = client.get(
        '/api/exportar/ordens-servico/csv/',
        HTTP_AUTHORIZATION=f'Bearer {token}'
    )
    
    assert response.status_code == 200
    assert response['Content-Type'] == 'text/csv'
```

---

## 9. RESUMO EXECUTIVO

| Padrão | Aplicação Proposta | Arquivos Principais | Impacto API | Complexidade | Risco |
|--------|-------------------|-------------------|-------------|-------------|-------|
| **Abstract Factory** | ✅ Manter | `exportacao/utils/` | Nenhum | Baixa | Nenhum |
| **Factory Method** | ✅ Manter | `accounts/permission_policies.py` | Nenhum | Baixa | Nenhum |
| **Builder** | ✅ Manter | `gemini_api/prompt_builder_pattern.py` | Nenhum | Média | Nenhum |
| **Singleton** | ❌ Não aplicável | — | — | — | — |
| **Facade** | ⚠️ Criar | `gemini_api/context_facade.py` | Nenhum | Média | Baixo |
| **Adapter** | ⚠️ Criar | `gemini_api/adapters.py` | Nenhum | Média | Baixo |
| **Composite** | ❌ Não aplicável | — | — | — | — |
| **Decorator** | ❌ Não aplicável | — | — | — | — |

---

## 10. DECISÕES E CONCLUSÕES FINAIS

### Padrões Implementados ✅

#### 1. Abstract Factory
```
STATUS: IMPLEMENTADO CORRETAMENTE
AÇÃO: MANTER SEM ALTERAÇÕES
MOTIVO: Resolve problema real de criação de múltiplos exportadores
```

#### 2. Factory Method
```
STATUS: IMPLEMENTADO CORRETAMENTE
AÇÃO: MANTER SEM ALTERAÇÕES
MOTIVO: Centraliza criação de policies de permissão de forma elegante
```

#### 3. Builder + Director
```
STATUS: IMPLEMENTADO CORRETAMENTE
AÇÃO: MANTER SEM ALTERAÇÕES
MOTIVO: Construção de prompts complexos de forma clara e reutilizável
```

### Padrões com Melhoria Possível ⚠️

#### 4. Facade
```
STATUS: PARCIALMENTE IMPLEMENTADO (funções soltas)
AÇÃO: REESTRUTURAÇÃO RECOMENDADA
MOTIVO: Simplificar views e centralizar coleta de contexto
RISCO: Baixo (refatoração interna, sem mudança de API)
ESFORÇO: Médio
```

#### 5. Adapter
```
STATUS: PARCIALMENTE IMPLEMENTADO (funções soltas)
AÇÃO: REESTRUTURAÇÃO RECOMENDADA
MOTIVO: Encapsular API Google, melhorar testabilidade
RISCO: Baixo (refatoração interna, sem mudança de API)
ESFORÇO: Médio
```

### Padrões Não Aplicáveis ❌

#### 6. Singleton
```
STATUS: NÃO APLICÁVEL
MOTIVO: Django com múltiplos workers = problemas thread-safety
        Padrões atuais funcionam melhor
CONCLUSÃO: NÃO IMPLEMENTAR ARTIFICIALMENTE
```

#### 7. Composite
```
STATUS: NÃO APLICÁVEL
MOTIVO: Nenhuma estrutura hierárquica recursiva identificada
        Relacionamentos 1:1 ou 1:N não necessitam Composite
CONCLUSÃO: NÃO IMPLEMENTAR ARTIFICIALMENTE
```

#### 8. Decorator
```
STATUS: NÃO APLICÁVEL
MOTIVO: Sem camada de serviço encapsulada
        Padrões Django (permission_classes, Signals) mais apropriados
CONCLUSÃO: NÃO IMPLEMENTAR ARTIFICIALMENTE
```

---

## 11. CRITÉRIO IMPORTANTE — EVITAR "CARGO CULT DESIGN"

### Princípio Aplicado

Durante esta análise, **NÃO foi criado nenhum padrão "apenas para constar"**.

Cada recomendação foi baseada em:
1. **Problema real identificado** no código atual
2. **Benefício concreto** que o padrão traria
3. **Impacto mínimo** em código existente
4. **Risco baixo** de regressão

### Padrões Não Forçados

- ❌ Singleton em Django multi-worker = RUIM
- ❌ Composite sem hierarquia recursiva = RUIM
- ❌ Decorator sem serviços encapsulados = RUIM

### Conclusão

O projeto está **bem estruturado**. As melhorias propostas são **opcionais** e visam apenas **melhorar manutenibilidade** de componentes específicos (Gemini AI).

---

## PRÓXIMAS ETAPAS

### FASE 1 (Atual) — ANÁLISE ✅
- ✅ Mapeamento completo do repositório
- ✅ Identificação de padrões existentes
- ✅ Análise dos 8 padrões
- ✅ Recomendações de implementação
- ✅ **Relatório Analise_8_padroes_projeto.md gerado**

### FASE 2 — IMPLEMENTAÇÃO (Aguardando Aprovação)

**Aguardando sua aprovação com a mensagem**:
```
"APROVADO. PODE IMPLEMENTAR."
```

Após aprovação, será implementado:
1. `gemini_api/adapters.py` — GeminiAdapter
2. `gemini_api/context_facade.py` — ContextFacade
3. Atualização de views para usar novos padrões
4. Testes automatizados
5. Atualização deste relatório com resultados

---

## REFERÊNCIAS E FONTES

- **Código-fonte**: `/accounts/`, `/exportacao/`, `/gemini_api/`, `/telemetria/`, `/alertas/`, `/ativos/`
- **Documentação**: `readme.md`, `EXPLICACAO_PROJETO_COMPLETA.md`, `Estrutura_API.md`
- **Configurações**: `app/settings.py`, `app/urls.py`
- **Padrões de Design**: Gang of Four, Design Patterns in Python

---

**Documento preparado em**: Setembro 2024  
**Versão**: 1.0 — ANÁLISE COMPLETA  
**Status**: Aguardando aprovação para FASE 2
