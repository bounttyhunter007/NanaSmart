# PADRÕES DE DESIGN - DOCUMENTO V3
## Informações Estruturadas para Diagramas de Classe
**Data:** 21/09/2026 | **Status:** ✅ Baseado em Código Real | **Escopo:** 8 Padrões

---

## 📋 ÍNDICE

1. [Abstract Factory Pattern](#1-abstract-factory-pattern) - Exportadores
2. [Factory Method Pattern](#2-factory-method-pattern) - Permissões
3. [Builder Pattern](#3-builder-pattern) - Prompts Gemini
4. [Facade Pattern (Parcial)](#4-facade-pattern-parcial) - Context Service
5. [Adapter Pattern (Parcial)](#5-adapter-pattern-parcial) - Gemini Client
6. [Observer Pattern (Implícito)](#6-observer-pattern-implícito) - Django Signals
7. [Singleton Pattern (Inaplicável)](#7-singleton-pattern-inaplicável)
8. [Composite Pattern (Inaplicável)](#8-composite-pattern-inaplicável)

---

# 1. ABSTRACT FACTORY PATTERN
## Exportadores (CSV, Excel, PDF)

### 📁 Localização
```
exportacao/utils/
├── base_exporter.py        [Interface ABC]
├── exporter_factory.py      [Factory Concreto]
├── csv_exporter.py          [Implementação CSV]
├── excel_exporter.py        [Implementação Excel]
└── pdf_exporter.py          [Implementação PDF]
```

### 🏗️ ESTRUTURA DE CLASSES

#### **Classe Base (Abstract)**
```
╔════════════════════════════════════════╗
║         <<abstract>>                   ║
║            Exportador                  ║
╠════════════════════════════════════════╣
║  MÉTODOS ABSTRATOS:                    ║
║  - exportar(nome, titulo, colunas,    ║
║             linhas) → HttpResponse     ║
╚════════════════════════════════════════╝
```

**Arquivo:** `exportacao/utils/base_exporter.py`

```python
from abc import ABC, abstractmethod
from django.http import HttpResponse

class Exportador(ABC):
    @abstractmethod
    def exportar(self, nome: str, titulo: str, colunas: list, linhas: list) -> HttpResponse:
        pass
```

---

#### **Implementação 1: CSV**
```
╔════════════════════════════════════════╗
║         ExportadorCSV                  ║
║      (implements Exportador)           ║
╠════════════════════════════════════════╣
║  MÉTODOS:                              ║
║  + exportar(nome: str,                 ║
║             titulo: str,               ║
║             colunas: list,             ║
║             linhas: list)              ║
║      → HttpResponse                    ║
║                                        ║
║  COMPORTAMENTO:                        ║
║  • Content-Type: text/csv              ║
║  • Encoding: UTF-8 com BOM             ║
║  • Delimiter: semicolon (;)            ║
║  • Headers: colunas[0]                 ║
║  • Rows: cada linha é um registro      ║
╚════════════════════════════════════════╝
```

**Arquivo:** `exportacao/utils/csv_exporter.py`

```python
import csv
from django.http import HttpResponse
from .base_exporter import Exportador

class ExportadorCSV(Exportador):
    def exportar(self, nome: str, titulo: str, colunas: list, linhas: list) -> HttpResponse:
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{nome}.csv"'
        response.write('\ufeff')  # BOM
        writer = csv.writer(response, delimiter=';')
        writer.writerow(colunas)
        for linha in linhas:
            writer.writerow(linha)
        return response
```

---

#### **Implementação 2: Excel**
```
╔════════════════════════════════════════╗
║      ExportadorExcel                   ║
║   (implements Exportador)              ║
╠════════════════════════════════════════╣
║  MÉTODOS:                              ║
║  + exportar(nome: str,                 ║
║             titulo: str,               ║
║             colunas: list,             ║
║             linhas: list)              ║
║      → HttpResponse                    ║
║                                        ║
║  COMPORTAMENTO:                        ║
║  • Content-Type: application/vnd.     ║
║    openxmlformats-office.             ║
║    spreadsheet                         ║
║  • Format: .xlsx (Workbook)            ║
║  • Estilos: Headers preto (#2E4057)    ║
║  • Zebra Striping: Linhas alternadas   ║
║  • Borders: Todas as células           ║
║  • Worksheet: titulo[0]                ║
╚════════════════════════════════════════╝
```

**Arquivo:** `exportacao/utils/excel_exporter.py`

```python
from io import BytesIO
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from .base_exporter import Exportador

class ExportadorExcel(Exportador):
    def exportar(self, nome: str, titulo: str, colunas: list, linhas: list) -> HttpResponse:
        wb = Workbook()
        ws = wb.active
        ws.title = titulo
        
        # Headers
        header_font = Font(name='Calibri', bold=True, color='FFFFFF', size=11)
        header_fill = PatternFill(start_color='2E4057', end_color='2E4057', fill_type='solid')
        header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        thin_border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'), bottom=Side(style='thin')
        )
        
        for col_idx, col_titulo in enumerate(colunas, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_titulo)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border
        
        # Data rows com zebra striping
        for row_idx, linha in enumerate(linhas, start=2):
            for col_idx, valor in enumerate(linha, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=valor)
                cell.border = thin_border
                if row_idx % 2 == 0:
                    cell.fill = PatternFill(start_color='F2F6FA', end_color='F2F6FA', fill_type='solid')
        
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(buffer.getvalue(), 
                              content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{nome}.xlsx"'
        return response
```

---

#### **Implementação 3: PDF**
```
╔════════════════════════════════════════╗
║      ExportadorPDF                     ║
║   (implements Exportador)              ║
╠════════════════════════════════════════╣
║  ATRIBUTOS:                            ║
║  - _orientacao: str = 'landscape'      ║
║                                        ║
║  MÉTODOS:                              ║
║  + __init__(orientacao='landscape')    ║
║  + exportar(nome: str,                 ║
║             titulo: str,               ║
║             colunas: list,             ║
║             linhas: list)              ║
║      → HttpResponse                    ║
║                                        ║
║  COMPORTAMENTO:                        ║
║  • Biblioteca: reportlab               ║
║  • Page Size: A4 landscape/portrait    ║
║  • Title Style: Color #2E4057, 16pt    ║
║  • Table: SimpleDocTemplate            ║
║  • Margins: 15mm (left/right),         ║
║             20mm (top)                 ║
╚════════════════════════════════════════╝
```

**Arquivo:** `exportacao/utils/pdf_exporter.py`

```python
from io import BytesIO
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from .base_exporter import Exportador

class ExportadorPDF(Exportador):
    def __init__(self, orientacao='landscape'):
        self._orientacao = orientacao

    def exportar(self, nome: str, titulo: str, colunas: list, linhas: list) -> HttpResponse:
        buffer = BytesIO()
        page_size = landscape(A4) if self._orientacao == 'landscape' else A4
        
        doc = SimpleDocTemplate(buffer, pagesize=page_size,
                               rightMargin=15*mm, leftMargin=15*mm,
                               topMargin=20*mm, bottomMargin=15*mm)
        
        elements = []
        # ... table construction ...
        
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nome}.pdf"'
        return response
```

---

### 🔧 FACTORY

```
╔════════════════════════════════════════╗
║      ExportadorFactory                 ║
║     (Factory Concreto)                 ║
╠════════════════════════════════════════╣
║  ATRIBUTOS CLASS:                      ║
║  - _registro: dict[str, type]          ║
║    └─ 'csv' → ExportadorCSV            ║
║    └─ 'excel' → ExportadorExcel        ║
║    └─ 'pdf' → ExportadorPDF            ║
║                                        ║
║  MÉTODOS CLASS:                        ║
║  + registrar(formato: str,             ║
║              exportador_cls: type)     ║
║      → None                            ║
║  + criar(formato: str)                 ║
║      → Exportador                      ║
║      ↳ Raises: ValueError              ║
╚════════════════════════════════════════╝
```

**Arquivo:** `exportacao/utils/exporter_factory.py`

```python
from .base_exporter import Exportador

class ExportadorFactory:
    _registro = {}

    @classmethod
    def registrar(cls, formato: str, exportador_cls: type):
        """Registra um novo exportador"""
        cls._registro[formato] = exportador_cls

    @classmethod
    def criar(cls, formato: str) -> Exportador:
        """Cria instância do exportador"""
        exportador_cls = cls._registro.get(formato)
        if not exportador_cls:
            raise ValueError(f"Formato de exportação '{formato}' não suportado.")
        return exportador_cls()
```

---

### 🔄 DIAGRAMA UML COMPLETO

```
                     ┌──────────────────────────┐
                     │   <<interface>>          │
                     │      Exportador          │
                     ├──────────────────────────┤
                     │  + exportar(...)         │
                     │    → HttpResponse        │
                     └──────────────────────────┘
                              ▲
                    ┌─────────┼─────────┐
                    │         │         │
        ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
        │ExportadorCSV  │ │ExportadorExcel│ │ ExportadorPDF │
        ├───────────────┤ ├───────────────┤ ├───────────────┤
        │+ exportar()   │ │+ exportar()    │ │- orientacao   │
        │  → CSV        │ │  → XLSX        │ │+ __init__()   │
        │  (UTF-8 BOM)  │ │  (Styled)      │ │+ exportar()   │
        │  (;)          │ │  (Zebra)       │ │  → PDF        │
        └───────────────┘ └───────────────┘ └───────────────┘

┌────────────────────────────────────────┐
│    ExportadorFactory (Registry)        │
├────────────────────────────────────────┤
│  - _registro = {                       │
│      'csv': ExportadorCSV,             │
│      'excel': ExportadorExcel,         │
│      'pdf': ExportadorPDF              │
│    }                                   │
│                                        │
│  + registrar(formato, classe)          │
│  + criar(formato) → Exportador         │
└────────────────────────────────────────┘
```

---

### 💡 USO (Exemplo Real)

```python
# Em exportacao/views.py
factory = ExportadorFactory()

# Criar CSV
exportador = factory.criar('csv')
response = exportador.exportar(
    nome='relatorio_ativos',
    titulo='Relatório de Ativos',
    colunas=['ID', 'Nome', 'Tipo', 'Status'],
    linhas=[[1, 'Motor 1', 'Motor Elétrico', 'Ativo'], ...]
)

# Criar Excel
exportador = factory.criar('excel')
response = exportador.exportar(...)

# Criar PDF
exportador = factory.criar('pdf')
response = exportador.exportar(...)
```

---

---

# 2. FACTORY METHOD PATTERN
## Permissões por Perfil de Usuário

### 📁 Localização
```
accounts/
├── permission_policies.py   [Policies e Factory]
└── permissions.py           [DRF Permissions]
```

### 🏗️ ESTRUTURA DE CLASSES

#### **Classe Base (Abstract)**
```
╔════════════════════════════════════════╗
║      <<abstract>>                      ║
║   BasePermissionPolicy                 ║
╠════════════════════════════════════════╣
║  MÉTODOS ABSTRATOS:                    ║
║  + can_access(user, method, obj,       ║
║               request) → bool          ║
╚════════════════════════════════════════╝
```

**Arquivo:** `accounts/permission_policies.py` (linhas 1-7)

```python
from abc import ABC, abstractmethod

class BasePermissionPolicy(ABC):
    """Contrato base para políticas de acesso por perfil."""

    @abstractmethod
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        raise NotImplementedError
```

---

#### **Implementação 1: GestorPolicy**
```
╔════════════════════════════════════════╗
║      GestorPolicy                      ║
║ (implements BasePermissionPolicy)      ║
╠════════════════════════════════════════╣
║  LÓGICA:                               ║
║  • if user not authenticated           ║
║    → return False                      ║
║  • if user.tipo_usuario in             ║
║      ['gestor', 'admin']               ║
║    → return True                       ║
║  • if user.is_superuser                ║
║    → return True                       ║
║  • else → return False                 ║
╚════════════════════════════════════════╝
```

```python
class GestorPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return user.tipo_usuario in ['gestor', 'admin'] or getattr(user, 'is_superuser', False)
```

---

#### **Implementação 2: TecnicoPolicy**
```
╔════════════════════════════════════════╗
║      TecnicoPolicy                     ║
║ (implements BasePermissionPolicy)      ║
╠════════════════════════════════════════╣
║  LÓGICA:                               ║
║  • if user not authenticated           ║
║    → return False                      ║
║  • if user.tipo_usuario == 'tecnico'   ║
║    → return True                       ║
║  • else → return False                 ║
╚════════════════════════════════════════╝
```

```python
class TecnicoPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return user.tipo_usuario == 'tecnico'
```

---

#### **Implementação 3: GestorOrReadOnlyPolicy**
```
╔════════════════════════════════════════╗
║   GestorOrReadOnlyPolicy               ║
║ (implements BasePermissionPolicy)      ║
╠════════════════════════════════════════╣
║  LÓGICA:                               ║
║  • if user not authenticated           ║
║    → return False                      ║
║  • if method in [GET, HEAD, OPTIONS]   ║
║    → return True (qualquer um)         ║
║  • if user é gestor/admin/superuser    ║
║    → return True                       ║
║  • else → return False                 ║
╚════════════════════════════════════════╝
```

```python
class GestorOrReadOnlyPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        
        if method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        return user.tipo_usuario in ['gestor', 'admin'] or getattr(user, 'is_superuser', False)
```

---

#### **Implementação 4: AuthenticatedNoDeleteForTecnicoPolicy**
```
╔════════════════════════════════════════╗
║ AuthenticatedNoDeleteForTecnicoPolicy  ║
║ (implements BasePermissionPolicy)      ║
╠════════════════════════════════════════╣
║  LÓGICA:                               ║
║  • if user not authenticated           ║
║    → return False                      ║
║  • if method in [GET, HEAD, OPTIONS]   ║
║    → return True                       ║
║  • if user é tecnico AND method DELETE ║
║    → return False (bloqueado)          ║
║  • if user é gestor/admin/superuser    ║
║    → return True                       ║
║  • else → return False                 ║
╚════════════════════════════════════════╝
```

```python
class AuthenticatedNoDeleteForTecnicoPolicy(BasePermissionPolicy):
    def can_access(self, user, method: str, obj=None, request=None) -> bool:
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        
        if method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        if user.tipo_usuario == 'tecnico' and method == 'DELETE':
            return False
        
        return user.tipo_usuario in ['gestor', 'admin'] or getattr(user, 'is_superuser', False)
```

---

### 🔧 FACTORY

```
╔════════════════════════════════════════╗
║    PermissionPolicyFactory             ║
║   (Factory Method Pattern)             ║
╠════════════════════════════════════════╣
║  ATRIBUTOS CLASS:                      ║
║  - _policies: dict[str, Policy]        ║
║    └─ 'gestor' → GestorPolicy()        ║
║    └─ 'tecnico' → TecnicoPolicy()      ║
║    └─ 'gestor_or_readonly' →           ║
║       GestorOrReadOnlyPolicy()         ║
║    └─ 'authenticated_no_delete...      ║
║       AuthenticatedNoDelete...Policy() ║
║                                        ║
║  MÉTODOS CLASS:                        ║
║  + create(policy_name: str)            ║
║      → BasePermissionPolicy            ║
║      ↳ Raises: ValueError              ║
║  + register(policy_name: str,          ║
║             policy: BasePermission...) ║
║      → None                            ║
╚════════════════════════════════════════╝
```

**Arquivo:** `accounts/permission_policies.py` (linhas 50-70)

```python
class PermissionPolicyFactory:
    """Fábrica simples para centralizar políticas por perfil de usuário."""

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
            raise ValueError(f"Política de permissão não registrada: {policy_name}") from exc

    @classmethod
    def register(cls, policy_name: str, policy: BasePermissionPolicy):
        cls._policies[policy_name] = policy
```

---

### 📋 INTEGRAÇÃO COM DRF

```
╔════════════════════════════════════════╗
║   IsGestor (DRF Permission)            ║
║ (Django REST Framework)                ║
╠════════════════════════════════════════╣
║  + has_permission(request, view)       ║
║      → bool                            ║
║  ↳ calls:                              ║
║    PermissionPolicyFactory.create()    ║
║    .can_access()                       ║
╚════════════════════════════════════════╝

╔════════════════════════════════════════╗
║   IsTecnico (DRF Permission)           ║
╠════════════════════════════════════════╣
║  + has_permission(request, view)       ║
║      → bool                            ║
╚════════════════════════════════════════╝

╔════════════════════════════════════════╗
║ IsGestorOrReadOnly (DRF Permission)    ║
╠════════════════════════════════════════╣
║  + has_permission(request, view)       ║
║      → bool                            ║
╚════════════════════════════════════════╝

╔════════════════════════════════════════╗
║ IsAuthenticatedNoDeleteForTecnico      ║
║     (DRF Permission)                   ║
╠════════════════════════════════════════╣
║  + has_permission(request, view)       ║
║      → bool                            ║
╚════════════════════════════════════════╝
```

**Arquivo:** `accounts/permissions.py`

```python
from rest_framework import permissions
from .permission_policies import PermissionPolicyFactory

class IsGestor(permissions.BasePermission):
    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('gestor')
        return policy.can_access(request.user, request.method)

class IsTecnico(permissions.BasePermission):
    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('tecnico')
        return policy.can_access(request.user, request.method)

class IsGestorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('gestor_or_readonly')
        return policy.can_access(request.user, request.method)

class IsAuthenticatedNoDeleteForTecnico(permissions.BasePermission):
    def has_permission(self, request, view):
        policy = PermissionPolicyFactory.create('authenticated_no_delete_for_tecnico')
        return policy.can_access(request.user, request.method)
```

---

### 🔄 DIAGRAMA UML COMPLETO

```
          ┌─────────────────────────────┐
          │   <<abstract>>              │
          │ BasePermissionPolicy        │
          ├─────────────────────────────┤
          │ + can_access(user, method,  │
          │             obj, request)   │
          │   → bool                    │
          └─────────────────────────────┘
                      ▲
        ┌─────┬───────┼───────┬─────┐
        │     │       │       │     │
    ┌──────┐┌──────┐┌──────┐┌──────────┐
    │Gestor││Tecnic││Gestor││Authentic │
    │Policy││Policy││OrRead││ated      │
    │      ││      ││Only  ││No Delete │
    │      ││      ││Policy││For Tecnic│
    └──────┘└──────┘└──────┘└──────────┘

┌──────────────────────────────────────────┐
│   PermissionPolicyFactory                │
├──────────────────────────────────────────┤
│  - _policies = {                         │
│      'gestor': GestorPolicy(),           │
│      'tecnico': TecnicoPolicy(),         │
│      'gestor_or_readonly': ...,          │
│      'authenticated_no_delete...': ...   │
│    }                                     │
│                                          │
│  + create(policy_name) → Policy          │
│  + register(policy_name, policy)         │
└──────────────────────────────────────────┘
         │ (used by)
         ▼
┌──────────────────────────────────────────┐
│   DRF Permission Classes                 │
├──────────────────────────────────────────┤
│  - IsGestor                              │
│  - IsTecnico                             │
│  - IsGestorOrReadOnly                    │
│  - IsAuthenticatedNoDeleteForTecnico     │
│                                          │
│  Cada uma chama:                         │
│  PermissionPolicyFactory.create()        │
│  policy.can_access()                     │
└──────────────────────────────────────────┘
```

---

### 💡 USO (Exemplo Real)

```python
# Em uma ViewSet do accounts
from rest_framework import viewsets
from .permissions import IsGestor, IsGestorOrReadOnly

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    
    # Qualquer um autenticado pode listar/GET
    # Apenas gestores podem criar/atualizar/deletar
    permission_classes = [IsGestorOrReadOnly]

# Em uma ViewSet do ativos
class EquipamentoViewSet(viewsets.ModelViewSet):
    queryset = Equipamento.objects.all()
    serializer_class = EquipamentoSerializer
    
    # Apenas gestores têm acesso total
    permission_classes = [IsGestor]
```

---

---

# 3. BUILDER PATTERN
## Construção de Prompts para Gemini API

### 📁 Localização
```
gemini_api/
├── prompt_builder_pattern.py   [Builder Interface e Concreto]
├── prompt.py                   [Produto Final]
├── prompt_director.py          [Director]
└── cliente.py                  [Gemini Integration]
```

### 🏗️ ESTRUTURA DE CLASSES

#### **Classe Produto**
```
╔════════════════════════════════════════╗
║          Prompt                        ║
║     (Produto Final)                    ║
╠════════════════════════════════════════╣
║  ATRIBUTOS:                            ║
║  - _texto: str                         ║
║                                        ║
║  MÉTODOS:                              ║
║  + __init__(texto: str)                ║
║  + obter_texto() → str                 ║
║  + __str__() → str                     ║
╚════════════════════════════════════════╝
```

**Arquivo:** `gemini_api/prompt.py`

```python
class Prompt:
    def __init__(self, texto: str):
        self._texto = texto

    def obter_texto(self) -> str:
        return self._texto

    def __str__(self) -> str:
        return self._texto
```

---

#### **Builder - Interface (Abstract)**
```
╔════════════════════════════════════════╗
║       <<abstract>>                     ║
║        PromptBuilder                   ║
╠════════════════════════════════════════╣
║  MÉTODOS ABSTRATOS:                    ║
║  + com_contexto(context_str) → self    ║
║  + com_alertas(alertas) → self         ║
║  + com_ordens(ordens, titulo) → self   ║
║  + com_telemetria(dados) → self        ║
║  + com_financeiro(dados) → self        ║
║  + com_instrucoes(texto) → self        ║
║  + com_pergunta(texto) → self          ║
║  + build() → Prompt                    ║
║  + reset() → None                      ║
╚════════════════════════════════════════╝
```

**Arquivo:** `gemini_api/prompt_builder_pattern.py` (linhas 1-38)

```python
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
```

---

#### **Builder - Implementação Concreta**
```
╔════════════════════════════════════════╗
║     PromptBuilderConcreto              ║
║  (implements PromptBuilder)            ║
╠════════════════════════════════════════╣
║  ATRIBUTOS:                            ║
║  - _blocos: list[str]                  ║
║  - _max_linhas: int = 5                ║
║                                        ║
║  MÉTODOS:                              ║
║  + __init__()                          ║
║  + reset() → None                      ║
║  + _truncar(linhas, max) → list        ║
║  + com_contexto(str) → self            ║
║  + com_alertas(list) → self            ║
║  + com_ordens(list, titulo) → self     ║
║  + com_telemetria(list) → self         ║
║  + com_financeiro(list) → self         ║
║  + com_instrucoes(str) → self          ║
║  + com_pergunta(str) → self            ║
║  + build() → Prompt                    ║
║                                        ║
║  PADRÃO:                               ║
║  • Fluent interface (retorna self)     ║
║  • Cada método adiciona bloco          ║
║  • Trunca listas para 5 itens máx      ║
║  • Adiciona prefixo de categoria       ║
╚════════════════════════════════════════╝
```

**Arquivo:** `gemini_api/prompt_builder_pattern.py` (linhas 40-130)

```python
class PromptBuilderConcreto(PromptBuilder):
    def __init__(self):
        self._blocos = []
        self._max_linhas = 5

    def reset(self):
        self._blocos = []

    def _truncar(self, linhas: list, max_linhas: int) -> list:
        if len(linhas) <= max_linhas:
            return linhas
        return linhas[:max_linhas] + [f"... ({len(linhas) - max_linhas} itens adicionais omitidos)"]

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
            linhas = [f"- {linha}" if not linha.startswith("-") else linha for linha in ordens]
            truncadas = self._truncar(linhas, self._max_linhas)
            if truncadas:
                self._blocos.append(f"\n{titulo}:\n" + "\n".join(truncadas))
        return self

    def com_telemetria(self, dados: list) -> 'PromptBuilder':
        if dados:
            truncadas = self._truncar(dados, self._max_linhas)
            if truncadas:
                self._blocos.append("\nTELEMETRIA RECENTE:\n" + "\n".join(truncadas))
        return self

    def com_financeiro(self, blocos_financeiros: list) -> 'PromptBuilder':
        if blocos_financeiros:
            self._blocos.append("\n".join(blocos_financeiros))
        return self

    def com_instrucoes(self, texto: str) -> 'PromptBuilder':
        if texto:
            self._blocos.append(f"\n{texto}")
        return self

    def com_pergunta(self, texto: str) -> 'PromptBuilder':
        if texto:
            self._blocos.append(f"\nPERGUNTA DO USUÁRIO:\n{texto}")
        return self

    def build(self) -> Prompt:
        resultado = "\n".join(self._blocos)
        return Prompt(resultado)
```

---

### 🎯 DIRECTOR

```
╔════════════════════════════════════════╗
║      PromptDirector                    ║
║   (Director - Orquestrador)            ║
╠════════════════════════════════════════╣
║  MÉTODOS ESTÁTICOS:                    ║
║  + montar_chat(builder, context,       ║
║                context_str, message)   ║
║      → Prompt                          ║
║                                        ║
║  + montar_analise_os(builder, context, ║
║                      context_str,      ║
║                      instruction, msg) ║
║      → Prompt                          ║
║                                        ║
║  + montar_ordens_nao_atribuidas(...)   ║
║      → Prompt                          ║
║                                        ║
║  + montar_financeiro(...)              ║
║      → Prompt                          ║
║                                        ║
║  RESPONSABILIDADE:                     ║
║  • Orquestra sequência de chamadas     ║
║  • Diferentes estratégias de montagem  ║
║  • Abstrai complexidade do builder     ║
╚════════════════════════════════════════╝
```

**Arquivo:** `gemini_api/prompt_director.py`

```python
from .prompt_builder_pattern import PromptBuilder
from .prompt import Prompt

class PromptDirector:
    @staticmethod
    def montar_chat(builder: PromptBuilder, context: dict, context_str: str, message: str) -> Prompt:
        builder.reset()
        builder.com_contexto(context_str)
        builder.com_alertas(context.get('alert_summary', []))
        builder.com_ordens(context.get('open_order_summary', []), "ORDENS EM ABERTO")
        
        kpis = context.get('equipment_kpis', [])
        if kpis:
            builder.com_ordens(kpis, "KPIs DE EQUIPAMENTOS")
            
        builder.com_telemetria(context.get('telemetry', []))
        builder.com_pergunta(message)
        return builder.build()

    @staticmethod
    def montar_analise_os(builder: PromptBuilder, context: dict, context_str: str, instruction: str, message: str) -> Prompt:
        builder.reset()
        builder.com_contexto(context_str)
        builder.com_ordens(context.get('assigned_order_summary', []), "ORDENS ATRIBUÍDAS")
        builder.com_ordens(context.get('unassigned_order_summary', []), "ORDENS SEM ATRIBUIÇÃO")
        builder.com_instrucoes(instruction)
        builder.com_pergunta(message)
        return builder.build()
        
    @staticmethod
    def montar_ordens_nao_atribuidas(builder: PromptBuilder, context: dict, context_str: str, instruction: str, message: str) -> Prompt:
        builder.reset()
        builder.com_contexto(context_str)
        builder.com_ordens(context.get('unassigned_order_summary', []), "ORDENS SEM ATRIBUIÇÃO (EXEMPLOS)")
        builder.com_instrucoes(instruction)
        builder.com_pergunta(message)
        return builder.build()

    @staticmethod
    def montar_financeiro(builder: PromptBuilder, context: dict, context_str: str, instruction: str, message: str) -> Prompt:
        builder.reset()
        builder.com_contexto(context_str)
        financial = context.get('financial_summary', {})
        if financial.get('top_equipment_costs'):
            builder.com_ordens(financial['top_equipment_costs'], "EQUIPAMENTOS COM MAIOR CUSTO")
        builder.com_instrucoes(instruction)
        builder.com_pergunta(message)
        return builder.build()
```

---

### 🔄 DIAGRAMA UML COMPLETO

```
┌──────────────────────────┐
│       Prompt             │
│  (Produto Final)         │
├──────────────────────────┤
│ - _texto: str            │
│                          │
│ + __init__(texto)        │
│ + obter_texto() → str    │
│ + __str__() → str        │
└──────────────────────────┘
           △
           │ (construído por)
           │
    ┌──────┴────────┐
    │               │
┌─────────────────────────┐     ┌──────────────────────────┐
│  <<abstract>>           │     │  PromptDirector          │
│   PromptBuilder         │     │  (Orquestrador)          │
├─────────────────────────┤     ├──────────────────────────┤
│+ com_contexto()→Builder │     │+ montar_chat()           │
│+ com_alertas()→Builder  │     │+ montar_analise_os()     │
│+ com_ordens()→Builder   │     │+ montar_ordens_...()     │
│+ com_telemetria()→Bl.   │     │+ montar_financeiro()     │
│+ com_financeiro()→Bl.   │     └──────────────────────────┘
│+ com_instrucoes()→Bl.   │
│+ com_pergunta()→Builder │
│+ build()→Prompt         │
│+ reset()→None           │
└─────────────────────────┘
           △
           │
    ┌──────┘
    │
┌──────────────────────────┐
│ PromptBuilderConcreto    │
├──────────────────────────┤
│ - _blocos: list[str]     │
│ - _max_linhas: int = 5   │
│                          │
│ + __init__()             │
│ + reset()                │
│ - _truncar()             │
│ + com_contexto()         │
│ + com_alertas()          │
│ + com_ordens()           │
│ + com_telemetria()       │
│ + com_financeiro()       │
│ + com_instrucoes()       │
│ + com_pergunta()         │
│ + build()→Prompt         │
└──────────────────────────┘
```

---

### 💡 USO (Exemplo Real)

```python
# Em gemini_api/views.py
from .prompt_builder_pattern import PromptBuilderConcreto
from .prompt_director import PromptDirector
from .cliente import generate_content

# Preparar dados de contexto
context = {
    'alert_summary': ['Alerta 1', 'Alerta 2'],
    'open_order_summary': ['OS 1', 'OS 2'],
    'telemetry': ['Sensor 1', 'Sensor 2'],
}

# Criar builder
builder = PromptBuilderConcreto()

# Usar director para montar prompt
prompt = PromptDirector.montar_chat(
    builder=builder,
    context=context,
    context_str="Contexto geral da empresa",
    message="Qual é o status dos equipamentos?"
)

# Enviar para Gemini
response, model_used = generate_content(
    system_instruction="Você é um especialista em manutenção",
    user_prompt=prompt.obter_texto()
)
```

---

---

# 4. FACADE PATTERN (PARCIAL)
## Context Service - Agregador de Dados

### 📁 Localização
```
gemini_api/
└── context_service.py   [Funções de contexto]
```

### 📋 SITUAÇÃO ATUAL

```
╔════════════════════════════════════════╗
║  CONTEXTO_SERVICE (Atual)              ║
║                                        ║
║  Funções ISOLADAS:                     ║
║  ✗ get_user_equipment_queryset()       ║
║  ✗ get_open_orders()                   ║
║  ✗ get_unassigned_orders()             ║
║  ✗ get_assigned_orders()               ║
║  ✗ get_active_alerts()                 ║
║  ✗ get_recent_telemetry()              ║
║  ... (mais funções)                    ║
║                                        ║
║  PROBLEMA: Views chamam múltiplas      ║
║  funções manualmente, montam contexto  ║
║  manualmente, alta acoplamento         ║
╚════════════════════════════════════════╝
```

**Arquivo:** `gemini_api/context_service.py` (linhas 1-60)

```python
from datetime import timedelta
from django.db.models import Sum, Count
from ativos.models import Equipamento
from alertas.models import Alerta
from manutencao.models import OrdemServico, HistoricoManutencao
from telemetria.models import Sensor, Telemetria
from manutencao.dashboards.views import KpiService

def get_user_equipment_queryset(user):
    """Retorna equipamentos visíveis para o usuário"""
    if user.tipo_usuario == 'admin':
        return Equipamento.objects.select_related('localizacao', 'empresa')
    
    if not user.empresa:
        return Equipamento.objects.none()
    
    return Equipamento.objects.filter(empresa=user.empresa).select_related('localizacao')

def get_open_orders(user):
    """Retorna ordens abertas"""
    equipamentos = get_user_equipment_queryset(user)
    return OrdemServico.objects.filter(
        equipamento__in=equipamentos,
        status__in=['pendente', 'andamento']
    ).select_related('equipamento', 'responsavel')

def get_unassigned_orders(user):
    """Retorna ordens sem responsável"""
    return get_open_orders(user).filter(responsavel__isnull=True)

def get_assigned_orders(user):
    """Retorna ordens atribuídas ao usuário"""
    return get_open_orders(user).filter(responsavel=user)

def get_active_alerts(user):
    """Retorna alertas ativos"""
    equipamentos = get_user_equipment_queryset(user)
    return Alerta.objects.filter(equipamento__in=equipamentos, status='ativo').select_related('equipamento')

def get_recent_telemetry(user, limit=5):
    """Retorna leituras recentes de sensores"""
    equipamentos = get_user_equipment_queryset(user)
    sensores = Sensor.objects.filter(equipamento__in=equipamentos, ativo=True).select_related('equipamento')
    resumo = []
    for sensor in sensores[:limit]:
        ultima_leitura = Telemetria.objects.filter(sensor=sensor).order_by('-timestamp').first()
        if not ultima_leitura:
            continue
        resumo.append(f"- Sensor {sensor.nome} ({sensor.get_tipo_display()}): {ultima_leitura.valor}{sensor.unidade_medida}")
    return resumo
```

---

### 🎯 PROPOSTA: ContextFacade

```
╔════════════════════════════════════════╗
║      ContextFacade                     ║
║    (Proposta de Implementação)         ║
╠════════════════════════════════════════╣
║  ATRIBUTOS:                            ║
║  - user: Usuario                       ║
║  - _equipment_queryset: QuerySet       ║
║                                        ║
║  MÉTODOS:                              ║
║  + __init__(user: Usuario)             ║
║  + build_chat_context() → dict         ║
║  + build_os_analysis_context() → dict  ║
║  + build_financial_context() → dict    ║
║  + get_equipment() → QuerySet          ║
║                                        ║
║  RESPONSABILIDADE:                     ║
║  • Centralizar coleta de contexto      ║
║  • Encapsular composição de dados      ║
║  • Reduzir acoplamento das views       ║
╚════════════════════════════════════════╝
```

---

### 💡 PROPOSTA DE USO

```python
# ANTES (Sem Facade)
from gemini_api.context_service import (
    get_user_equipment_queryset,
    get_open_orders,
    get_active_alerts,
    get_recent_telemetry,
)

def chat_view(request):
    equipamentos = get_user_equipment_queryset(request.user)
    ordens_abertas = get_open_orders(request.user)
    alertas = get_active_alerts(request.user)
    telemetria = get_recent_telemetry(request.user)
    
    context = {
        'equipment': equipamentos,
        'open_orders': ordens_abertas,
        'alerts': alertas,
        'telemetry': telemetria,
    }
    # ... rest of view

# DEPOIS (Com Facade)
from gemini_api.context_facade import ContextFacade

def chat_view(request):
    facade = ContextFacade(request.user)
    context = facade.build_chat_context()
    # ... rest of view
```

---

---

# 5. ADAPTER PATTERN (PARCIAL)
## Gemini API Integration

### 📁 Localização
```
gemini_api/
└── cliente.py   [Integração direta com Google]
```

### 📋 SITUAÇÃO ATUAL

```
╔════════════════════════════════════════╗
║  CLIENTE.PY (Atual - Sem Adapter)      ║
║                                        ║
║  Problemas:                            ║
║  ✗ Google types expostos (Content,     ║
║    GenerateContentConfig)              ║
║  ✗ Detalhes de modelo hardcoded        ║
║  ✗ Lógica de fallback acoplada         ║
║  ✗ Difícil testar sem API real         ║
║  ✗ Difícil mudar de provider (ex:      ║
║    OpenAI, Claude, local LLM)          ║
║                                        ║
║  Função Atual:                         ║
║  generate_content(                     ║
║      system_instruction,               ║
║      user_prompt,                      ║
║      history=None,                     ║
║      model_candidates=None,            ║
║      temperature=0.4                   ║
║  ) → (response_text, model_name)       ║
╚════════════════════════════════════════╝
```

**Arquivo:** `gemini_api/cliente.py` (linhas 1-80)

```python
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(override=True)

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or api_key == "CHAVEAQKUI":
        return None
    
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

def is_gemini_available():
    return get_gemini_client() is not None

def generate_content(system_instruction, user_prompt, history=None, model_candidates=None, temperature=0.4):
    client = get_gemini_client()
    if not client:
        raise RuntimeError("A chave GEMINI_API_KEY não está configurada ou é inválida.")
    
    if model_candidates is None:
        model_candidates = [
            "gemini-3.5-flash",
            "gemini-2.5-flash",
            "gemini-flash-latest",
        ]
    
    contents = []
    if history:
        for item in history:
            role = "user" if item.get("role") == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=item.get("text", ""))]
                )
            )
    
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_prompt)]
        )
    )
    
    last_error = None
    for model_name in model_candidates:
        try:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
            )
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
            return response.text, model_name
        except Exception as e:
            # ... error handling
            last_error = e
            # continue to next model
```

---

### 🎯 PROPOSTA: GeminiAdapter

```
╔════════════════════════════════════════╗
║       <<interface>>                    ║
║        IAAdapter                       ║
╠════════════════════════════════════════╣
║  MÉTODOS ABSTRATOS:                    ║
║  + is_available() → bool               ║
║  + gerar_conteudo(                     ║
║      instrucao_sistema: str,           ║
║      pergunta_usuario: str,            ║
║      historico: list = None,           ║
║      temperatura: float = 0.4          ║
║    ) → tuple(str, str)                 ║
║      ↳ returns: (resposta, nome_modelo)║
╚════════════════════════════════════════╝

╔════════════════════════════════════════╗
║      GeminiAdapter                     ║
║   (implements IAAdapter)               ║
╠════════════════════════════════════════╣
║  ATRIBUTOS:                            ║
║  - _client: genai.Client               ║
║  - _modelos: list[str]                 ║
║                                        ║
║  MÉTODOS:                              ║
║  + __init__()                          ║
║  + _get_client() → genai.Client        ║
║  + is_available() → bool               ║
║  + gerar_conteudo(...) → tuple         ║
║  - _montar_historico(list) → list      ║
║                                        ║
║  ENCAPSULA:                            ║
║  • Toda lógica Google Gemini           ║
║  • types.Content, types.Part           ║
║  • Modelos disponíveis                 ║
║  • Fallback de modelos                 ║
║  • Tratamento de erros Google-specific ║
╚════════════════════════════════════════╝
```

---

### 💡 PROPOSTA DE USO

```python
# ANTES (Acoplado ao Google)
from gemini_api.cliente import generate_content

response_text, model = generate_content(
    system_instruction="Você é expert em manutenção",
    user_prompt="Qual é o problema?",
    temperature=0.4
)

# DEPOIS (Desacoplado via Adapter)
from gemini_api.adapters import GeminiAdapter

adapter = GeminiAdapter()
if adapter.is_available():
    response_text, model = adapter.gerar_conteudo(
        instrucao_sistema="Você é expert em manutenção",
        pergunta_usuario="Qual é o problema?",
        temperatura=0.4
    )
```

---

---

# 6. OBSERVER PATTERN (IMPLÍCITO)
## Django Signals - Sistema de Eventos

### 📁 Localização
```
telemetria/signals.py     [Observer 1]
alertas/signals.py        [Observer 2]
ativos/signals.py         [Observer 3]
```

### 🏗️ ESTRUTURA DE EVENTOS

#### **PIPELINE DE OBSERVADORES**

```
     TELEMETRIA.POST_SAVE
            │
            │ (sensor.valor atualizado)
            │
            ▼
    ┌──────────────────────────┐
    │  checar_limites_         │
    │  telemetria()            │
    │  @receiver               │
    │  (post_save, Telemetria) │
    │                          │
    │  Lógica:                 │
    │  • Calcula percentual    │
    │  • Determina nível       │
    │    (baixo/medio/critico) │
    │  • Cria/atualiza Alerta  │
    └──────────────────────────┘
            │
            │ (cria ALERTA)
            │
            ▼
    ALERTA.POST_SAVE
            │
            │
            ▼
    ┌──────────────────────────┐
    │  vincular_ordem_         │
    │  servico_ao_alerta()     │
    │  @receiver               │
    │  (post_save, Alerta)     │
    │                          │
    │  Lógica:                 │
    │  • Map nivel → prioridade│
    │  • Cria OrdemServico     │
    │  • Escalation de nível   │
    └──────────────────────────┘
            │
            │ (cria O.S. CORRETIVA)
            │
            ▼
    ORDEM_SERVICO criada


     EQUIPAMENTO.POST_SAVE
            │
            │ (horimetro atualizado)
            │
            ▼
    ┌──────────────────────────┐
    │  verificar_planos_       │
    │  por_horimetro()         │
    │  @receiver               │
    │  (post_save,             │
    │   Equipamento)           │
    │                          │
    │  Lógica:                 │
    │  • Itera planos ativos   │
    │  • Verifica threshold    │
    │  • Cria O.S. PREDITIVA   │
    └──────────────────────────┘
```

---

### 🔍 OBSERVER 1: Telemetria Signal

```
╔════════════════════════════════════════╗
║  @receiver(post_save, sender=Telemetria)
║                                        ║
║  checar_limites_telemetria()           ║
╠════════════════════════════════════════╣
║  ENTRADA:                              ║
║  • instance: Telemetria (nova leitura) ║
║  • created: bool (é novo?)             ║
║                                        ║
║  LÓGICA:                               ║
║  1. Valida: sensor ativo? tem limite?  ║
║  2. Calcula: percentual = valor/limite ║
║  3. Determina nível:                   ║
║     - < 70% → (sem alerta)             ║
║     - 70-85% → 'baixo'                 ║
║     - 85-100% → 'medio'                ║
║     - >= 100% → 'critico'              ║
║  4. Deduplication: alerta já existe?   ║
║  5. Escalation: nível piorou?          ║
║  6. Criação: Alerta.objects.create()   ║
║     ↳ Dispara ALERTA.POST_SAVE         ║
║                                        ║
║  SAÍDA:                                ║
║  • Alerta criado/atualizado            ║
║  • Dispara próximo observer             ║
╚════════════════════════════════════════╝
```

**Arquivo:** `telemetria/signals.py`

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Telemetria
from alertas.models import Alerta

@receiver(post_save, sender=Telemetria)
def checar_limites_telemetria(sender, instance, created, **kwargs):
    """Dispara automaticamente a cada nova leitura de sensor."""
    if not created:
        return

    sensor = instance.sensor
    if not sensor.ativo:
        return

    valor = instance.valor
    equipamento = sensor.equipamento
    limite = sensor.limite_alerta

    if limite is None or limite <= 0:
        return

    percentual = (valor / limite) * 100

    # Configuráveis por sensor
    limite_baixo = sensor.limite_alerta_baixo_pct or 70.0
    limite_medio = sensor.limite_alerta_medio_pct or 85.0
    limite_critico = sensor.limite_alerta_critico_pct or 100.0

    # Determina nível
    if percentual >= limite_critico:
        nivel = 'critico'
    elif percentual >= limite_medio:
        nivel = 'medio'
    elif percentual >= limite_baixo:
        nivel = 'baixo'
    else:
        return

    tipo_alerta = f"Alerta de {sensor.get_tipo_display()}"

    # Deduplication
    alerta_existente = Alerta.objects.filter(
        equipamento=equipamento,
        tipo_alerta=tipo_alerta,
        status='ativo'
    ).first()

    if alerta_existente:
        ordem_nivel = {'baixo': 1, 'medio': 2, 'critico': 3}
        if ordem_nivel[nivel] > ordem_nivel[alerta_existente.nivel]:
            alerta_existente.nivel = nivel
            alerta_existente.descricao = f"Situação agravada em {equipamento.nome}. ..."
            alerta_existente.save()  # → Dispara ALERTA.POST_SAVE
        return

    # Create novo alerta
    Alerta.objects.create(
        equipamento=equipamento,
        tipo_alerta=tipo_alerta,
        nivel=nivel,
        descricao=f"Anomalia detectada em {equipamento.nome}. ..."
    )  # → Dispara ALERTA.POST_SAVE
```

---

### 🔍 OBSERVER 2: Alerta Signal

```
╔════════════════════════════════════════╗
║  @receiver(post_save, sender=Alerta)   ║
║                                        ║
║  vincular_ordem_servico_ao_alerta()    ║
╠════════════════════════════════════════╣
║  ENTRADA:                              ║
║  • instance: Alerta (criado/atualizado)║
║  • created: bool (é novo?)             ║
║                                        ║
║  LÓGICA:                               ║
║  1. Valida: alerta ativo?              ║
║  2. Map nível → prioridade:            ║
║     - 'baixo' → 'baixa'                ║
║     - 'medio' → 'media'                ║
║     - 'critico' → 'critica'            ║
║  3. Verifica: O.S. ativa existe?       ║
║  4. Criação ou Escalação:              ║
║     - Se não existe → Cria nova        ║
║     - Se existe → Escalona prioridade  ║
║  5. Saída: O.S. CORRETIVA criada       ║
║                                        ║
║  RESULTADO:                            ║
║  • Ordem de Serviço CORRETIVA          ║
║  • Tipo: 'corretiva'                   ║
║  • Prioridade: map(nivel)              ║
╚════════════════════════════════════════╝
```

**Arquivo:** `alertas/signals.py`

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Alerta
from manutencao.models import OrdemServico

@receiver(post_save, sender=Alerta)
def vincular_ordem_servico_ao_alerta(sender, instance, created, **kwargs):
    """Cria O.S. automática quando alerta é criado."""
    if instance.status != 'ativo':
        return

    prioridade_map = {
        'critico': 'critico',
        'medio': 'media',
        'baixo': 'baixa'
    }
    
    prioridade_alvo = prioridade_map.get(instance.nivel, 'baixa')
    titulo_os = f"MANUTENÇÃO: {instance.tipo_alerta}"

    # Verifica se existe O.S. ativa
    os_ativa = OrdemServico.objects.filter(
        equipamento=instance.equipamento,
        status__in=['pendente', 'andamento'],
        titulo=titulo_os
    ).first()

    if not os_ativa:
        # Cria nova
        OrdemServico.objects.create(
            equipamento=instance.equipamento,
            titulo=titulo_os,
            descricao=f"O.S. vinculada ao alerta: {instance.tipo_alerta}.\n{instance.descricao}",
            prioridade=prioridade_alvo,
            tipo_os='corretiva',
            status='pendente'
        )
    else:
        # Escalona
        ordem_peso = {'baixa': 1, 'media': 2, 'critica': 3}
        if ordem_peso[prioridade_alvo] > ordem_peso[os_ativa.prioridade]:
            os_ativa.prioridade = prioridade_alvo
            os_ativa.descricao += f"\n\n[ATUALIZAÇÃO]: Nível escalado para {instance.nivel.upper()}."
            os_ativa.save()
```

---

### 🔍 OBSERVER 3: Equipamento Signal (Planos de Manutenção)

```
╔════════════════════════════════════════╗
║  @receiver(post_save,                  ║
║            sender=Equipamento)         ║
║                                        ║
║  verificar_planos_por_horimetro()      ║
╠════════════════════════════════════════╣
║  ENTRADA:                              ║
║  • instance: Equipamento               ║
║  • horimetro: float (atualizado)       ║
║                                        ║
║  LÓGICA:                               ║
║  1. Itera: equipamento.planos_        ║
║            manutencao.filter(ativo)    ║
║  2. Para cada plano:                   ║
║     • proximo_disparo =                ║
║       horimetro_ultima_os +            ║
║       intervalo_horas                  ║
║  3. Verifica: horimetro >= disparo?    ║
║  4. Deduplication: O.S. existe?        ║
║  5. Criação: O.S. PREDITIVA            ║
║  6. Update: plano.horimetro_ultima_os  ║
║                                        ║
║  RESULTADO:                            ║
║  • Ordem de Serviço PREDITIVA          ║
║  • Tipo: 'preditiva'                   ║
║  • Descr: baseado em plano             ║
╚════════════════════════════════════════╝
```

**Arquivo:** `ativos/signals.py`

```python
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Equipamento
from manutencao.models import OrdemServico

@receiver(post_save, sender=Equipamento)
def verificar_planos_por_horimetro(sender, instance, **kwargs):
    """Dispara O.S. preditiva quando horímetro atinge threshold."""
    for plano in instance.planos_manutencao.filter(ativo=True):
        proximo_disparo = plano.horimetro_ultima_os + plano.intervalo_horas

        if instance.horimetro < proximo_disparo:
            continue

        # Deduplication
        ja_existe = OrdemServico.objects.filter(
            equipamento=instance,
            tipo_os='preditiva',
            titulo__contains=plano.nome_servico,
            status__in=['pendente', 'andamento']
        ).exists()

        if ja_existe:
            continue

        # Cria O.S. preditiva
        OrdemServico.objects.create(
            equipamento=instance,
            titulo=f"[PREDITIVA] {plano.nome_servico}",
            descricao=(
                f"Manutenção preditiva programada por horímetro.\n"
                f"Plano: {plano.nome_servico}\n"
                f"Horímetro de disparo: {instance.horimetro:.1f}h\n"
                f"Intervalo do plano: a cada {plano.intervalo_horas:.0f}h"
            ),
            tipo_os='preditiva',
            prioridade=plano.prioridade,
            status='pendente',
        )

        # Atualiza plano para próximo ciclo
        plano.horimetro_ultima_os = instance.horimetro
        plano.save(update_fields=['horimetro_ultima_os'])
```

---

### 🔄 DIAGRAMA DE EVENTOS (UML)

```
┌─────────────────────────────┐
│    Telemetria (Model)       │
│  (Nova leitura de sensor)   │
└─────────────────────────────┘
            │
            │ post_save signal
            │
            ▼
┌──────────────────────────────────────┐
│  checar_limites_telemetria()         │
│  @receiver(post_save, Telemetria)    │
│                                      │
│  • Calcula percentual                │
│  • Determina nível (baixo/medio/c.)  │
│  • Cria/Atualiza Alerta              │
└──────────────────────────────────────┘
            │
            │ creates
            │
            ▼
┌─────────────────────────────┐
│    Alerta (Model)           │
│  (Alerta criado/atualizado) │
└─────────────────────────────┘
            │
            │ post_save signal
            │
            ▼
┌──────────────────────────────────────┐
│  vincular_ordem_servico_ao_alerta()  │
│  @receiver(post_save, Alerta)        │
│                                      │
│  • Map nível → prioridade            │
│  • Cria/Escalona OrdemServico        │
└──────────────────────────────────────┘
            │
            │ creates
            │
            ▼
┌─────────────────────────────┐
│  OrdemServico (Model)       │
│  (Tipo: CORRETIVA)          │
└─────────────────────────────┘


┌─────────────────────────────┐
│   Equipamento (Model)       │
│  (Horímetro atualizado)     │
└─────────────────────────────┘
            │
            │ post_save signal
            │
            ▼
┌──────────────────────────────────────┐
│  verificar_planos_por_horimetro()    │
│  @receiver(post_save, Equipamento)   │
│                                      │
│  • Itera planos ativos               │
│  • Verifica threshold de horas       │
│  • Cria OrdemServico PREDITIVA       │
└──────────────────────────────────────┘
            │
            │ creates
            │
            ▼
┌─────────────────────────────┐
│  OrdemServico (Model)       │
│  (Tipo: PREDITIVA)          │
└─────────────────────────────┘
```

---

---

# 7. SINGLETON PATTERN (INAPLICÁVEL)

### ❌ Razão: Multi-Worker Django

Em ambientes de produção, Django roda com múltiplos workers (processos/threads):

```
┌──────────────────────────────────────────┐
│         Aplicação Django (Produção)      │
├──────────────────────────────────────────┤
│                                          │
│  Worker 1      Worker 2       Worker 3   │
│  ┌─────────┐  ┌─────────┐   ┌─────────┐ │
│  │ Instance│  │ Instance│   │ Instance│ │
│  │   1     │  │   2     │   │   3     │ │
│  │         │  │         │   │         │ │
│  │ Dados:  │  │ Dados:  │   │ Dados:  │ │
│  │ A = 10  │  │ A = 20  │   │ A = 15  │ │
│  └─────────┘  └─────────┘   └─────────┘ │
│       ✗             ✗            ✗       │
│    NÃO SÃO A MESMA INSTÂNCIA!           │
│                                          │
│    Problema: Estado não é compartilhado │
└──────────────────────────────────────────┘
```

**Cada worker Python carrega módulos independentemente:**
- Worker 1 cria Singleton(A)
- Worker 2 cria Singleton(B) ← instância diferente!
- Worker 3 cria Singleton(C) ← instância diferente!

### ✅ Python/Django JÁ usam Singleton (implicitamente)

#### 1. Django Settings

```python
from django.conf import settings

DEBUG = settings.DEBUG
DATABASES = settings.DATABASES

# Internamente:
# LazySettings com _wrapped que cacheia configuração
# Cada worker tem SUA PRÓPRIA instância, mas é único dentro do worker
```

#### 2. Logging Module

```python
import logging

logger1 = logging.getLogger('myapp')
logger2 = logging.getLogger('myapp')

# logger1 is logger2 → True
# Python mantém cache de loggers em _loggers dict
```

#### 3. Django ORM Models

```python
from accounts.models import Usuario

# Cada import carrega a classe UMA VEZ
# Python module system = Singleton
usuarios_model_1 = Usuario
usuarios_model_2 = Usuario
# usuarios_model_1 is usuarios_model_2 → True
```

#### 4. Database Connections

```python
from django.db import connection

conn1 = connection.connection
conn2 = connection.connection
# connection pool singleton
```

### ⚠️ CONCLUSÃO

**NÃO implementar Singleton explícito** porque:
- ❌ Não funciona em multi-worker (cada worker tem sua instância)
- ❌ Sem compartilhamento real de estado
- ✅ Python/Django já usam Singleton implicitamente onde necessário
- ✅ Usar Factory Pattern (como PermissionPolicyFactory) é seguro e funciona

---

---

# 8. COMPOSITE PATTERN (INAPLICÁVEL)

### ❌ Razão: Estrutura de Dados Não-Hierárquica

O Composite Pattern é para estruturas **árvore/hierárquica** onde componentes contêm subcomponentes.

```
Exemplo de Composite (Ideal):
┌─────────────────────┐
│  Department         │
├─────────────────────┤
│  name: "Engineering"│
│  employees: [...]   │
│  + add(Department)  │
│  + getSize() → int  │
└─────────────────────┘
        │
        ├─ Sub-Department
        │  ├─ Engineers
        │  └─ QA
        │
        └─ Sub-Department
           ├─ Managers
           └─ Admins
```

### 🔍 ESTRUTURA DO NANASMART

```
Equipamento (NÃO é hierárquico)
├─ nome: str
├─ tipo: str
├─ sensores: QuerySet[Sensor] ← FLAT, não recursivo
├─ planos_manutencao: QuerySet[Plano] ← FLAT
├─ ordens_servico: QuerySet[OS] ← FLAT
└─ alertas: QuerySet[Alerta] ← FLAT

Alerta (NÃO é hierárquico)
├─ equipamento: FK[Equipamento]
├─ nivel: str
└─ status: str

OrdemServico (NÃO é hierárquico)
├─ equipamento: FK
├─ responsavel: FK[Usuario]
├─ tipo_os: str
└─ historico: OneToOne[HistoricoManutencao]
```

**Não há:**
- ❌ Equipamentos dentro de Equipamentos
- ❌ Ordens dentro de Ordens
- ❌ Alertas dentro de Alertas
- ❌ Estrutura recursiva

### ✅ ALTERNATIVA: Query Relationships

Se for necessário agrupar:

```python
# NÃO use Composite
# class EquipamentoComposite:
#     def add(self, equipment): ...

# USE relacionamentos Django
equipamentos = Equipamento.objects.filter(empresa=empresa)
for eq in equipamentos:
    sensores = eq.sensores.all()
    ordens = eq.ordens_servico.all()
    alertas = eq.alertas.all()
```

---

---

## 📊 RESUMO GERAL

| # | Padrão | Arquivo(s) | Status | Diagrama UML | Implementação |
|---|--------|-----------|--------|-------------|----------------|
| 1 | Abstract Factory | exportacao/utils/*.py | ✅ OK | Exportador hierarchy | 3 implementações (CSV, Excel, PDF) |
| 2 | Factory Method | accounts/permission_policies.py | ✅ OK | Policy hierarchy | 4 policies + Factory |
| 3 | Builder | gemini_api/prompt_builder_pattern.py | ✅ OK | Builder fluent interface | PromptDirector + Concrete |
| 4 | Facade | gemini_api/context_service.py | ⚠️ Parcial | Funções isoladas | Proposta: ContextFacade |
| 5 | Adapter | gemini_api/cliente.py | ⚠️ Parcial | Integração direta | Proposta: GeminiAdapter |
| 6 | Observer | telemetria/alertas/ativos/signals.py | ✅ OK | Django Signal Chain | 3 receivers (pós-save events) |
| 7 | Singleton | - | ❌ Inaplicável | Multi-worker problema | Python/Django implícito |
| 8 | Composite | - | ❌ Inaplicável | Sem estrutura hierárquica | Usar relationships Django |

---

## 📝 NOTAS FINAIS

✅ **Implementados Corretamente (3):**
- Abstract Factory (Exportadores)
- Factory Method (Permissões)
- Builder (Prompts)

⚠️ **Parcialmente Implementados (2) - Propostas de Melhoria:**
- Facade (ContextFacade para aggregar dados)
- Adapter (GeminiAdapter para encapsular Google API)

❌ **Inaplicáveis (3):**
- Singleton (Multi-worker Django)
- Composite (Sem hierarquias)
- (8º padrão não especificado - use conforme necessário)

---

**Documento Gerado:** 21/09/2026
**Formato:** Estruturado para Diagramas UML
**Fonte:** Código real do repositório NanaSmart
