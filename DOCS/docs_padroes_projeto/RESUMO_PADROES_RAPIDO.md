# RESUMO EXECUTIVO — 8 PADRÕES DE PROJETO
## NanaSmart — Guia Rápido de Decisões

---

## 1️⃣ ABSTRACT FACTORY ✅ MANTER

### O que é
Padrão para criar **famílias de objetos relacionados** de forma consistente.

### Onde Está
`exportacao/utils/exporter_factory.py` + implementações (CSV, Excel, PDF)

### Como Está Hoje
```python
ExportadorFactory.registrar('csv', ExportadorCSV)
ExportadorFactory.registrar('excel', ExportadorExcel)
ExportadorFactory.registrar('pdf', ExportadorPDF)

exportador = ExportadorFactory.criar('csv')
```

✅ **Implementação perfeita** — Sem mudanças necessárias.

### Por Que Usar
- ✅ Múltiplos formatos de exportação (CSV, Excel, PDF)
- ✅ Fácil adicionar novo formato sem alterar código existente
- ✅ Cada exportador implementa interface consistente

### Por Que NÃO Usar
❌ Não há motivo — já está implementado corretamente.

### Como Será
**SEM MUDANÇAS** — Deixar como está.

---

## 2️⃣ FACTORY METHOD ✅ MANTER

### O que é
Padrão para criar objetos através de um **método centralizado** em vez de instanciação direta.

### Onde Está
`accounts/permission_policies.py`

### Como Está Hoje
```python
class PermissionPolicyFactory:
    _policies = {
        'gestor': GestorPolicy(),
        'tecnico': TecnicoPolicy(),
        'gestor_or_readonly': GestorOrReadOnlyPolicy(),
    }
    
    @classmethod
    def create(cls, policy_name: str):
        return cls._policies[policy_name]

# Uso
policy = PermissionPolicyFactory.create('gestor')
```

✅ **Implementação perfeita** — Sem mudanças necessárias.

### Por Que Usar
- ✅ Políticas de permissão centralizadas
- ✅ Fácil registrar novas policies
- ✅ Evita `if/elif` em múltiplos lugares

### Por Que NÃO Usar
❌ Não há motivo — já está implementado corretamente.

### Como Será
**SEM MUDANÇAS** — Deixar como está.

---

## 3️⃣ BUILDER ✅ MANTER

### O que é
Padrão para construir **objetos complexos passo-a-passo** de forma clara e flexível.

### Onde Está
`gemini_api/prompt_builder_pattern.py`

### Como Está Hoje
```python
builder = PromptBuilderConcreto()

prompt = (builder
    .com_contexto(context_str)
    .com_alertas(alertas)
    .com_ordens(ordens, "ORDENS ABERTAS")
    .com_telemetria(dados)
    .com_pergunta(mensagem)
    .build())
```

✅ **Implementação excelente** — Sem mudanças necessárias.

### Por Que Usar
- ✅ Construção incremental de prompts complexos
- ✅ Interface fluida e legível
- ✅ Fácil reutilizar builder para diferentes tipos de prompts

### Por Que NÃO Usar
❌ Não há motivo — já está implementado corretamente.

### Como Será
**SEM MUDANÇAS** — Deixar como está.

---

## 4️⃣ SINGLETON ❌ NÃO USAR

### O que é
Padrão que garante **uma única instância** de uma classe em todo o programa.

### Onde Está
❌ Não implementado (e não deve ser)

### Por Que USAR
- ✅ Acesso centralizado a recursos únicos
- ✅ Logger compartilhado
- ✅ Configurações globais

### Por Que NÃO Usar (NESTE PROJETO)
⚠️ **Django com múltiplos workers** = PROBLEMA PERIGOSO

```
Worker 1     Worker 2     Worker 3
   ↓            ↓            ↓
   └────────────┼────────────┘
                ↓
         Instância ÚNICA compartilhada
         ❌ Race conditions
         ❌ Vazamento de conexões
         ❌ Problemas de sincronização
```

### Candidatos Analisados e Rejeitados
- ❌ PermissionPolicyFactory — Já é singleton-like sem precisar de padrão
- ❌ Gemini Client — Criar por request é mais seguro
- ❌ Database — Django ORM já gerencia corretamente

### Como Está Hoje
**Não existe Singleton** — Não precisa existir.

### Como Será
**SEM MUDANÇAS** — Não implementar Singleton.

**Alternativa melhor**: Factory pattern (já usando) ou criar instâncias por request.

---

## 5️⃣ FACADE ⚠️ MELHORAR (OPCIONAL)

### O que é
Padrão que fornece **uma interface única e simplificada** para um subsistema complexo.

### Onde Está
`gemini_api/context_service.py` (PARCIAL — funções soltas)

### Como Está Hoje ❌ COMPLEXO
```python
# Código cliente tem que fazer muito manualmente
context = {
    'company_name': user.empresa.nome,
    'total_equipment': Equipamento.objects.filter(...).count(),
    'open_orders': get_open_orders(user),  # Função 1
    'unassigned_orders': get_unassigned_orders(user),  # Função 2
    'alert_summary': build_alert_summary(...),  # Função 3
    'open_order_summary': build_order_summary(...),  # Função 4
    'equipment_kpis': build_equipment_kpi_summary(user),  # Função 5
    'telemetry': get_recent_telemetry(user),  # Função 6
    'financial_summary': get_financial_summary(),  # Função 7
}
# Muito acoplamento e código bagunçado
```

### Por Que Usar
- ✅ Simplificar views complexas
- ✅ Centralizar coleta de contexto
- ✅ Fácil reutilizar em múltiplos endpoints
- ✅ Melhor manutenibilidade

### Por Que NÃO Usar
- ❌ Se o projeto ficar simples, não precisa Façade
- ❌ Se há apenas um lugar usando, pode ser overhead

### Como Será ✅ SIMPLES
```python
# PROPOSTO: Criar classe ContextFacade

class ContextFacade:
    def __init__(self, user):
        self.user = user
    
    def build_chat_context(self):
        return {
            'company_name': self._get_company_name(),
            'total_equipment': self._count_equipment(),
            'open_orders': self._get_open_orders(),
            'alert_summary': self._build_alert_summary(),
            'telemetry': self._get_recent_telemetry(),
            # ... tudo encapsulado
        }
    
    def build_os_analysis_context(self):
        # Contexto para análise de ordens
        ...
    
    # Métodos privados (implementação oculta)
    def _get_company_name(self):
        ...
```

**Novo Uso (UMA LINHA)**:
```python
# Simplicidade
facade = ContextFacade(user)
context = facade.build_chat_context()
```

### Impacto
- ✅ **Endpoints**: SEM MUDANÇA
- ✅ **Risco**: Baixo (refatoração interna)
- ✅ **Esforço**: Médio

---

## 6️⃣ ADAPTER ⚠️ MELHORAR (OPCIONAL)

### O que é
Padrão que **converte interface incompatível** em uma que o sistema espera.

### Onde Está
`gemini_api/cliente.py` (PARCIAL — funções soltas)

### Como Está Hoje ❌ ACOPLADO
```python
# Cliente precisa conhecer detalhes do Google Gemini
from google import genai
from google.genai import types

response = client.models.generate_content(
    model="gemini-3.5-flash",  # Conhece modelo específico
    contents=types.Content(...),  # Conhece tipos internos
    config=types.GenerateContentConfig(...),  # Conhece config
)

# Se Google mudar API → Precisa ajustar aqui também
```

### Por Que Usar
- ✅ Proteger código contra mudanças da API externa
- ✅ Facilitar troca de provider (OpenAI, Anthropic, etc.)
- ✅ Melhorar testabilidade (mockar adapter)
- ✅ Centralizar detalhes do Gemini em um lugar

### Por Que NÃO Usar
- ❌ Se integração é simples e não muda
- ❌ Se apenas um lugar usa a API
- ❌ Se quer keep it simple

### Como Será ✅ ENCAPSULADO
```python
# PROPOSTO: Criar classe GeminiAdapter

class GeminiAdapter:
    def is_available(self) -> bool:
        return self.client is not None
    
    def gerar_conteudo(self, 
                       instrucao_sistema: str, 
                       pergunta_usuario: str,
                       historico: list = None,
                       temperatura: float = 0.4) -> tuple:
        """
        Interface interna simples.
        Tudo de Google encapsulado aqui.
        """
        # Detalhes Google ficam aqui:
        # - types.Content
        # - types.GenerateContentConfig
        # - Tentativa de múltiplos modelos
        # - Tratamento de erros
        
        return response_text, model_name

# Novo Uso (SIMPLES)
adapter = GeminiAdapter()
if adapter.is_available():
    resposta, modelo = adapter.gerar_conteudo(
        "Você é assistente",
        "Qual é 2+2?"
    )
```

### Benefício Real
Se Google mudar API → Alterar apenas em `GeminiAdapter`, não em múltiplos places.

### Impacto
- ✅ **Endpoints**: SEM MUDANÇA
- ✅ **Risco**: Baixo (refatoração interna)
- ✅ **Esforço**: Médio

---

## 7️⃣ COMPOSITE ❌ NÃO USAR

### O que é
Padrão para trabalhar com **estruturas de árvore** onde partes e composições têm mesma interface.

### Exemplo de Uso
```python
# Seria algo tipo:
interface = Component
├── EquipamentoFolha (implementa Component)
└── GrupoEquipamentos (contém lista de Components)

# Tratamento uniforme:
def contar_alertas(componente):
    return componente.contar_alertas()  # Funciona tanto para folha quanto grupo
```

### Onde Está
❌ Não existe (e não deve ser implementado)

### Por Que Usar
- ✅ Estruturas hierárquicas profundas (árvore de setores, grupos)
- ✅ Operações recursivas

### Por Que NÃO Usar (NESTE PROJETO)
⚠️ **NÃO HÁ hierarquia recursiva necessária**

- ❌ Equipamentos não contêm outros equipamentos
- ❌ Alertas não formam árvore
- ❌ Localizações são apenas 1:1
- ❌ Sem caso de uso real

### Candidatos Analisados e Rejeitados
- ❌ Equipamento + Localização → Apenas 1:1, não é Composite
- ❌ PlanoManutencao → Relacionamento 1:N, não hierárquico
- ❌ Alertas → Apenas agrupados por equipamento, não recursivos

### Como Está
**Nenhuma estrutura Composite** — E está certo assim.

### Como Será
**SEM MUDANÇAS** — Não implementar Composite.

---

## 8️⃣ DECORATOR ❌ NÃO USAR

### O que é
Padrão para **adicionar comportamentos dinamicamente** a objetos sem alterar suas classes.

### Exemplo de Uso
```python
# Seria algo tipo:
classe_original = Serviço()
classe_com_log = ServiçoComLog(classe_original)
classe_com_cache = ServiçoComCache(classe_com_log)

# Comportamentos compostos dinamicamente
resultado = classe_com_cache.fazer_algo()  # Com cache + com log
```

### Onde Está
❌ Não existe (e não deveria ser forçado)

### Por Que Usar
- ✅ Adicionar logging a serviços
- ✅ Adicionar cache
- ✅ Adicionar auditoria
- ✅ Compor comportamentos dinamicamente

### Por Que NÃO Usar (NESTE PROJETO)
⚠️ **Django DRF resolve essas necessidades de forma melhor**

- ❌ Sem camada de "serviços" clara para decorar
- ❌ ViewSets chamam ORM diretamente
- ❌ Permissões → `permission_classes` (melhor)
- ❌ Logging → Signals e `@receiver` (mais apropriado)
- ❌ Cache → ORM do Django já cuida

### Candidatos Analisados e Rejeitados
- ❌ Logging → Signals e decorators Python já fazem isso
- ❌ Permissões → `permission_classes` é padrão DRF
- ❌ Cache → ORM do Django é suficiente
- ❌ Auditoria → Signals já implementam

### Como Está
**Nenhum Decorator implementado** — E está certo assim.

### Como Será
**SEM MUDANÇAS** — Não forçar Decorator.

---

## 📊 TABELA COMPARATIVA FINAL

| Padrão | Status | Ação | Risco | Esforço | Impacto API |
|--------|--------|------|-------|---------|-------------|
| **Abstract Factory** | ✅ OK | MANTER | Nenhum | 0h | Nenhum |
| **Factory Method** | ✅ OK | MANTER | Nenhum | 0h | Nenhum |
| **Builder** | ✅ OK | MANTER | Nenhum | 0h | Nenhum |
| **Singleton** | ❌ Inaplicável | IGNORAR | Alto | — | — |
| **Facade** | ⚠️ Parcial | IMPLEMENTAR | Baixo | 4-6h | Nenhum |
| **Adapter** | ⚠️ Parcial | IMPLEMENTAR | Baixo | 4-6h | Nenhum |
| **Composite** | ❌ Inaplicável | IGNORAR | — | — | — |
| **Decorator** | ❌ Inaplicável | IGNORAR | — | — | — |

---

## 🎯 DECISÃO FINAL

### ✅ Implementações Já Feitas (3 Padrões)
```
Abstract Factory ✅ PERFEITO
Factory Method   ✅ PERFEITO
Builder          ✅ PERFEITO
```

**Ação**: Deixar como está, não mexer.

### ⚠️ Implementações Recomendadas (2 Padrões - Opcional)
```
Facade  ⚠️ Simplificaria views
Adapter ⚠️ Encapsularia Gemini
```

**Ação**: Implementar após aprovação (baixo risco, médio esforço, alto benefício).

### ❌ Padrões Rejeitados (3 Padrões)
```
Singleton  ❌ Perigoso em multi-worker
Composite  ❌ Sem hierarquia recursiva
Decorator  ❌ DRF tem soluções melhores
```

**Ação**: Não forçar. Código está correto sem eles.

---

## 🚀 PRÓXIMOS PASSOS

Se aprovado para implementação:

**Etapa 1** (2-3h): Criar `GeminiAdapter`
- Arquivo: `gemini_api/adapters.py`
- Encapsula API Google
- Testes de unidade

**Etapa 2** (2-3h): Criar `ContextFacade`
- Arquivo: `gemini_api/context_facade.py`
- Centraliza coleta de contexto
- Testes de unidade

**Etapa 3** (1-2h): Atualizar views
- `gemini_api/views.py`
- Usar novo adapter e façade
- Testes de integração

**Etapa 4** (1h): Validação
- Executar testes
- Verificar endpoints
- Django check

**Tempo Total**: ~8h, Risco: Baixo, Benefício: Alto

---

**Documento**: Resumo Executivo  
**Status**: Pronto para Implementação  
**Próximo**: Aguardando aprovação

