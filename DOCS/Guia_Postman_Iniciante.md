# 🏆 Tutorial Completo: Testando a API no Postman (Do Zero ao Avançado)

> Este guia foi escrito para quem nunca usou uma API antes. Ele explica cada conceito, cada clique no Postman e cada campo JSON que você precisa preencher. Siga na ordem.

---

## 📚 PARTE 0: Conceitos Básicos (Leia Antes de Tudo)

### O que é uma API?
Uma API é como um **garçom** em um restaurante. Você (o cliente/Postman) faz um pedido, o garçom (API) leva para a cozinha (servidor/banco de dados) e traz a resposta de volta para você.

### O que é o Postman?
O Postman é um programa gratuito que permite enviar "pedidos" para a API sem precisar de um site ou aplicativo pronto. É a ferramenta padrão da indústria para testar APIs.

### Os 4 Métodos HTTP que você vai usar:

| Método   | O que faz              | Analogia                          |
|----------|------------------------|-----------------------------------|
| **GET**    | Busca/Lista dados      | "Me mostra o cardápio"            |
| **POST**   | Cria um dado novo      | "Quero fazer um pedido novo"      |
| **PUT**    | Substitui um dado inteiro | "Troca todo o meu pedido"      |
| **PATCH**  | Altera parte de um dado | "Só muda a bebida do meu pedido" |
| **DELETE** | Apaga um dado          | "Cancela meu pedido"             |

### O que é JSON?
JSON é o "idioma" que a API fala. É um formato de texto estruturado com chaves e valores. Exemplo:
```json
{
    "nome": "Motor Principal",
    "tipo": "Motor Elétrico"
}
```
**Regras do JSON:**
- Sempre use **aspas duplas** `"` (nunca aspas simples).
- Números e booleanos (`true`/`false`) **não** levam aspas.
- Separe os campos com **vírgula**, mas **não** coloque vírgula no último campo.

### Códigos de Resposta (Status Codes):

| Código | Significado            | O que fazer                       |
|--------|------------------------|-----------------------------------|
| **200**  | OK, deu certo          | Tudo funcionou                    |
| **201**  | Criado com sucesso     | O dado foi salvo no banco         |
| **400**  | Erro no seu pedido     | Revise o JSON enviado             |
| **401**  | Não autenticado        | Você esqueceu o Token ou ele expirou |
| **403**  | Sem permissão          | Seu perfil não pode fazer isso    |
| **404**  | Não encontrado         | O ID não existe ou não é da sua empresa |

---

## 🔧 PARTE 1: Configurando o Postman

### Passo 1.1: Criando uma Collection
1. Abra o Postman.
2. No painel esquerdo, clique em **"New" → "Collection"**.
3. Nomeie como **"Plataforma Manutenção"**.
4. Todas as suas requisições ficarão organizadas dentro desta pasta.

### Passo 1.2: Como descobrir o formato JSON de cada endpoint
Antes de sair testando, você precisa saber **quais campos** enviar. Para isso existe o **Swagger**:
1. Com o servidor rodando (`python manage.py runserver`), abra no navegador: `http://localhost:8000/api/schema/swagger-ui/`
2. Você verá uma lista de todos os endpoints organizados por categoria.
3. Clique em qualquer endpoint (ex: `POST /api/equipamentos/`).
4. Clique em **"Try it out"**.
5. O Swagger mostra o **JSON de exemplo** com todos os campos possíveis. Use esse JSON como modelo no Postman.

**Dica**: O **ReDoc** (`http://localhost:8000/api/schema/redoc/`) mostra a mesma informação, mas em um formato mais limpo para leitura.

---

## 🔐 PARTE 2: Autenticação (O Primeiro Passo Obrigatório)

### 2.1 Fazendo Login
Sem login, a API bloqueia tudo. Vamos pegar o token.

1. Na sua Collection, clique em **"Add Request"**. Nomeie como **"Login"**.
2. Configure:
   - **Método**: `POST`
   - **URL**: `http://localhost:8000/api/auth/token/`
3. Vá na aba **Body**:
   - Selecione **raw**.
   - No dropdown ao lado, mude de "Text" para **JSON**.
   - Cole:
   ```json
   {
       "username": "admin",
       "password": "admin123"
   }
   ```
4. Clique em **Send**.
5. **Resultado esperado** (Status 200):
   ```json
   {
       "refresh": "eyJhbGciOiJI... (código longo)",
       "access": "eyJhbGciOiJI... (outro código longo)"
   }
   ```
6. **Copie o valor do campo `access`** (sem as aspas). Esse é o seu Token.

### 2.2 Configurando o Token para todas as requisições
Para não precisar colar o token em cada requisição:
1. Clique na sua **Collection** "Plataforma Manutenção" (no painel esquerdo).
2. Vá na aba **Authorization**.
3. Em **Type**, escolha **Bearer Token**.
4. Em **Token**, cole o código `access` que você copiou.
5. Clique em **Save**.
6. Agora, em cada nova requisição, na aba Auth, escolha **"Inherit auth from parent"**. O Postman usará automaticamente o token da Collection.

### 2.3 Verificando quem você é
1. Crie uma nova requisição chamada **"Meu Perfil"**.
2. **Método**: `GET` | **URL**: `http://localhost:8000/api/auth/me/`
3. Clique em **Send**.
4. **Resultado**: Seus dados completos (nome, empresa, tipo de usuário, etc.).

### 2.4 Trocando a Senha
1. **Método**: `POST` | **URL**: `http://localhost:8000/api/auth/change-password/`
2. **Body (JSON)**:
   ```json
   {
       "senha_atual": "admin123",
       "nova_senha": "NovaSenha@2024",
       "confirmar_nova_senha": "NovaSenha@2024"
   }
   ```
3. **Resultado esperado**: Status 200.

### ❌ 2.5 Teste de ERRO: Login com senha errada
1. Use o endpoint de Login com senha incorreta:
   ```json
   {
       "username": "admin",
       "password": "senhaErrada"
   }
   ```
2. **Resultado esperado**: Status **401 Unauthorized**.

### ❌ 2.6 Teste de ERRO: Requisição sem token
1. Em qualquer requisição, vá na aba **Auth** e mude para **No Auth**.
2. Tente acessar `GET /api/equipamentos/`.
3. **Resultado esperado**: Status **401**.

---

## 🏢 PARTE 3: Empresas

### 3.1 Listar Empresas
- **Método**: `GET` | **URL**: `http://localhost:8000/api/empresas/`
- Clique em **Send**. Você verá a lista de empresas cadastradas.

### 3.2 Criar Nova Empresa
- **Método**: `POST` | **URL**: `http://localhost:8000/api/empresas/`
- **Body (JSON)** — Campos disponíveis:
  ```json
  {
      "nome": "TechIndustria LTDA",
      "cnpj": "12.345.678/0001-99",
      "email": "contato@techindustria.com",
      "telefone": "(11) 99999-0000",
      "endereco": "Rua das Máquinas, 100 - São Paulo"
  }
  ```

| Campo      | Tipo   | Obrigatório? | Observação                        |
|------------|--------|--------------|-----------------------------------|
| nome       | texto  | ✅ Sim       |                                   |
| cnpj       | texto  | ✅ Sim       | Deve ser único no sistema         |
| email      | email  | ✅ Sim       | Formato: usuario@dominio.com      |
| telefone   | texto  | ❌ Não       |                                   |
| endereco   | texto  | ❌ Não       |                                   |

- **Resultado esperado**: Status **201 Created** com o objeto criado (incluindo o `id`).

### 3.3 Ver Detalhes de Uma Empresa
- **Método**: `GET` | **URL**: `http://localhost:8000/api/empresas/1/`
- O número `1` é o ID da empresa. Troque pelo ID real.

### 3.4 Atualizar Empresa (Parcial)
- **Método**: `PATCH` | **URL**: `http://localhost:8000/api/empresas/1/`
- **Body**: Envie apenas o campo que quer mudar:
  ```json
  {
      "telefone": "(21) 88888-1111"
  }
  ```

### ❌ 3.5 Teste de ERRO: CNPJ duplicado
- Tente criar outra empresa com o mesmo CNPJ da primeira.
- **Resultado esperado**: Status **400** com mensagem de CNPJ já existente.

### ❌ 3.6 Teste de ERRO: Técnico tenta acessar empresas
- Faça login como técnico (`username: tecnico1, password: 123`).
- Tente `GET /api/empresas/`.
- **Resultado esperado**: Status **403 Forbidden**.

---

## 👤 PARTE 4: Usuários

### 4.1 Listar Usuários
- **Método**: `GET` | **URL**: `http://localhost:8000/api/usuarios/`

### 4.2 Criar Novo Usuário
- **Método**: `POST` | **URL**: `http://localhost:8000/api/usuarios/`
- **Body (JSON)**:
  ```json
  {
      "username": "joao_tecnico",
      "password": "Senha@123",
      "email": "joao@empresa.com",
      "first_name": "João",
      "last_name": "Silva",
      "empresa": 1,
      "tipo_usuario": "tecnico",
      "cargo": "Eletricista Sênior",
      "telefone": "(11) 91234-5678"
  }
  ```

| Campo         | Tipo   | Obrigatório? | Valores aceitos                  |
|---------------|--------|--------------|----------------------------------|
| username      | texto  | ✅ Sim       | Único no sistema                 |
| password      | texto  | ✅ Sim       | Mínimo 6 caracteres              |
| email         | email  | ❌ Não       |                                  |
| first_name    | texto  | ❌ Não       |                                  |
| last_name     | texto  | ❌ Não       |                                  |
| empresa       | número | ❌ Não       | ID de uma empresa existente      |
| tipo_usuario  | texto  | ✅ Sim       | `admin`, `gestor` ou `tecnico`   |
| cargo         | texto  | ❌ Não       | Ex: "Mecânico", "Eletricista"    |
| telefone      | texto  | ❌ Não       |                                  |

---

## ⚙️ PARTE 5: Equipamentos (Ativos)

### 5.1 Listar Equipamentos
- **Método**: `GET` | **URL**: `http://localhost:8000/api/equipamentos/`
- **Filtros via URL** (adicione na URL como parâmetros):
  - `?status=ativo` → Só ativos
  - `?search=Motor` → Busca por nome
  - `?ordering=-nome` → Ordena por nome (decrescente)
- **Exemplo com filtro**: `http://localhost:8000/api/equipamentos/?status=ativo&search=Motor`

### 5.2 Criar Equipamento
- **Método**: `POST` | **URL**: `http://localhost:8000/api/equipamentos/`
- **Body (JSON)**:
  ```json
  {
      "nome": "Compressor de Ar Industrial",
      "tipo": "Compressor",
      "fabricante": "Atlas Copco",
      "modelo": "GA 90+",
      "numero_serie": "AC-2024-001",
      "data_instalacao": "2024-03-15",
      "horimetro": 150.5,
      "status": "ativo",
      "empresa": 1
  }
  ```

| Campo            | Tipo   | Obrigatório? | Valores aceitos / Observação         |
|------------------|--------|--------------|--------------------------------------|
| nome             | texto  | ✅ Sim       |                                      |
| tipo             | texto  | ✅ Sim       | Ex: "Motor Elétrico", "Compressor"   |
| fabricante       | texto  | ❌ Não       |                                      |
| modelo           | texto  | ❌ Não       |                                      |
| numero_serie     | texto  | ✅ Sim       | **Deve ser único** no sistema        |
| data_instalacao  | data   | ❌ Não       | Formato: `AAAA-MM-DD`               |
| horimetro        | número | ❌ Não       | Horas de operação (padrão: 0)        |
| status           | texto  | ❌ Não       | `ativo`, `manutencao` ou `inativo`   |
| empresa          | número | ✅ Sim       | ID da empresa                        |

**Nota de Ouro sobre o Horímetro**:
- **Cenário de Máquina Nova**: Se você não enviar o campo `horimetro`, o equipamento será criado com **0.0 horas**.
- **Cenário de Máquina Usada (Retroativo)**: Se a máquina já está em uso na fábrica, você **deve** enviar o valor atual (ex: `150.5`). 
- **Por que isso importa?** O horímetro é o "coração" da Manutenção Preditiva (veja a Parte 12). Os planos de manutenção usarão esse valor exato como ponto de partida para não disparar ordens atrasadas incorretamente.

### ❌ 5.3 Teste de ERRO: Número de série duplicado
- Tente criar outro equipamento com o mesmo `numero_serie`.
- **Resultado esperado**: Status **400**.

### ❌ 5.4 Teste de ERRO: Técnico tenta criar equipamento
- Logado como técnico, tente `POST /api/equipamentos/`.
- **Resultado esperado**: Status **403 Forbidden** (técnico só pode ler).

---

## 📍 PARTE 6: Localização de Equipamentos

### 6.1 Criar Localização
- **Método**: `POST` | **URL**: `http://localhost:8000/api/localizacao/`
- **Body (JSON)**:
  ```json
  {
      "equipamento": 1,
      "setor": "Linha de Produção A - Setor 3"
  }
  ```

| Campo         | Tipo   | Obrigatório? | Observação                          |
|---------------|--------|--------------|-------------------------------------|
| equipamento   | número | ✅ Sim       | ID do equipamento (relação 1-para-1)|
| setor         | texto  | ✅ Sim       | Ex: "Sala de Máquinas", "Galpão B" |

**Importante**: Cada equipamento só pode ter **uma** localização. Se tentar criar duas para o mesmo equipamento, receberá erro.

---

## 📡 PARTE 7: Sensores (O Coração do IoT)

### 7.1 Listar Sensores
- **Método**: `GET` | **URL**: `http://localhost:8000/api/telemetria/sensores/`

### 7.2 Criar Sensor com Limite Customizado
- **Método**: `POST` | **URL**: `http://localhost:8000/api/telemetria/sensores/`
- **Body (JSON)**:
  ```json
  {
      "equipamento": 1,
      "tipo_sensor": "temperatura",
      "unidade_medida": "°C",
      "limite_alerta": 85.0,
      "descricao": "Sensor de temperatura do rolamento principal",
      "ativo": true
  }
  ```

| Campo          | Tipo     | Obrigatório? | Valores aceitos                              |
|----------------|----------|--------------|----------------------------------------------|
| equipamento    | número   | ✅ Sim       | ID do equipamento                            |
| tipo_sensor    | texto    | ✅ Sim       | `temperatura`, `vibracao`, `pressao`, `corrente`, `umidade` |
| unidade_medida | texto    | ✅ Sim       | Ex: `°C`, `mm/s`, `bar`, `A`, `%`           |
| limite_alerta  | decimal  | ❌ Não       | Se não enviar, o sistema preenche automaticamente |
| descricao      | texto    | ❌ Não       |                                              |
| ativo          | booleano | ❌ Não       | `true` ou `false` (padrão: `true`)           |

**Sobre o `limite_alerta`**: Este é o valor que define quando o sistema gera um alerta **Crítico** (100% do limite). Os outros níveis são calculados automaticamente:
- **Baixo**: quando o valor do sensor atinge 70% do limite.
- **Médio**: quando o valor atinge 85% do limite.
- **Crítico**: quando o valor atinge ou ultrapassa 100% do limite.

### 7.3 Verificar se o Limite foi Preenchido Automaticamente
1. Crie um sensor **sem** o campo `limite_alerta`.
2. Faça um `GET` no sensor criado.
3. O campo `limite_alerta` deve estar preenchido com o valor padrão para aquele tipo de equipamento.

---

## 📊 PARTE 8: Telemetria (Simulando Dados de Sensores)

### 8.1 Enviar Leitura de Sensor
- **Método**: `POST` | **URL**: `http://localhost:8000/api/telemetria/leituras/`
- **Body (JSON)**:
  ```json
  {
      "sensor": 1,
      "valor": 60.0
  }
  ```

| Campo  | Tipo    | Obrigatório? | Observação                        |
|--------|---------|--------------|-----------------------------------|
| sensor | número  | ✅ Sim       | ID do sensor                      |
| valor  | decimal | ✅ Sim       | O valor lido pelo sensor          |

**O que acontece nos bastidores**: O sistema compara automaticamente o `valor` com o `limite_alerta` do sensor e decide se gera um alerta.

### 8.2 Experimento: Testando os 3 Níveis de Alerta
Supondo que o sensor tem `limite_alerta = 100.0`:

**Teste 1 — Alerta Baixo** (70% de 100 = 70):
```json
{ "sensor": 1, "valor": 75.0 }
```
→ Verifique: `GET /api/alertas/` deve mostrar um alerta **baixo**.
→ Verifique: `GET /api/ordens-servico/` deve mostrar uma O.S. com prioridade **baixo**.

**Teste 2 — Alerta Médio** (85% de 100 = 85):
```json
{ "sensor": 1, "valor": 90.0 }
```
→ O alerta anterior deve **escalar** para **medio**. A O.S. também deve subir de prioridade.

**Teste 3 — Alerta Crítico** (100% de 100 = 100):
```json
{ "sensor": 1, "valor": 105.0 }
```
→ O alerta deve escalar para **critico** e a O.S. para **critico**.

### 8.3 Listar Leituras
- **Método**: `GET` | **URL**: `http://localhost:8000/api/telemetria/leituras/`

### ❌ 8.4 Teste de ERRO: Valor inválido
```json
{ "sensor": 1, "valor": "QUENTE" }
```
- **Resultado esperado**: Status **400** — o campo `valor` deve ser numérico.

---

## 🚨 PARTE 9: Alertas

Os alertas são gerados **automaticamente** pelo sistema. Você não precisa criá-los manualmente.

### 9.1 Listar Alertas
- **Método**: `GET` | **URL**: `http://localhost:8000/api/alertas/`
- **Filtros úteis**:
  - `?nivel=critico` → Só alertas críticos.
  - `?status=ativo` → Só alertas ativos (não resolvidos).

### 9.2 Resolver um Alerta
- **Método**: `PATCH` | **URL**: `http://localhost:8000/api/alertas/1/`
- **Body (JSON)**:
  ```json
  {
      "status": "resolvido"
  }
  ```

| Campo  | Valores aceitos                      |
|--------|--------------------------------------|
| status | `ativo`, `resolvido` ou `ignorado`   |
| nivel  | `baixo`, `medio` ou `critico`        |

---

## 🛠️ PARTE 10: Ordens de Serviço (O.S.)

### 10.1 Listar O.S.
- **Método**: `GET` | **URL**: `http://localhost:8000/api/ordens-servico/`
- **Filtros**:
  - `?status=pendente` → Só pendentes.
  - `?prioridade=critico` → Só críticas.
  - `?responsavel=5` → Só do técnico com ID 5.
  - `?search=Motor` → Busca no título e descrição.

### 10.2 Criar O.S. Manualmente
- **Método**: `POST` | **URL**: `http://localhost:8000/api/ordens-servico/`
- **Body (JSON)**:
  ```json
  {
      "equipamento": 1,
      "titulo": "Troca de rolamento preventiva",
      "descricao": "Rolamento do eixo principal com desgaste visível.",
      "prioridade": "medio",
      "status": "pendente",
      "tipo_os": "preventiva",
      "responsavel": null
  }
  ```

| Campo        | Tipo   | Obrigatório? | Valores aceitos                                     |
|--------------|--------|--------------|-----------------------------------------------------|
| equipamento  | número | ✅ Sim       | ID do equipamento                                   |
| titulo       | texto  | ✅ Sim       |                                                     |
| descricao    | texto  | ✅ Sim       |                                                     |
| prioridade   | texto  | ❌ Não       | `baixo`, `medio` ou `critico`                       |
| status       | texto  | ❌ Não       | `pendente`, `andamento`, `concluida`, `cancelada`   |
| tipo_os      | texto  | ❌ Não       | `corretiva`, `preditiva`, `preventiva` (padrão)     |
| responsavel  | número | ❌ Não       | ID de um usuário (ou `null`)                        |

**Campos automáticos** (você NÃO envia, o servidor preenche):
- `data_abertura` → Preenchido com a data/hora atual.
- `data_conclusao` → Preenchido quando o status mudar para `concluida`.

### 10.3 Técnico "Pega" uma O.S.
Quando o técnico quer assumir uma tarefa:
- **Método**: `PATCH` | **URL**: `http://localhost:8000/api/ordens-servico/1/`
- **Body**:
  ```json
  {
      "responsavel": 5,
      "status": "andamento"
  }
  ```
  (Onde `5` é o ID do próprio técnico logado.)

### 10.4 Concluir uma O.S.
- **Método**: `PATCH` | **URL**: `http://localhost:8000/api/ordens-servico/1/`
- **Body**:
  ```json
  {
      "status": "concluida"
  }
  ```
  O campo `data_conclusao` será preenchido automaticamente pelo servidor.

### ❌ 10.5 Teste de ERRO: Técnico B tenta editar O.S. do Técnico A
1. Logue como Técnico A e pegue uma O.S. (seção 10.3).
2. Logue como Técnico B e tente acessar `GET /api/ordens-servico/` — a O.S. do Técnico A **não** deve aparecer na lista.
3. Se tentar `PATCH /api/ordens-servico/{id}/`, receberá **404 Not Found**.

---

## 📋 PARTE 11: Histórico de Manutenção

### 11.1 Registrar Histórico (Após Concluir a O.S.)
- **Método**: `POST` | **URL**: `http://localhost:8000/api/historico-manutencao/`
- **Body (JSON)**:
  ```json
  {
      "ordem_servico": 1,
      "descricao_servico": "Substituído rolamento NSK 6205 do eixo principal.",
      "data_execucao": "2024-06-15",
      "custo_pecas": 250.00,
      "custo_mao_de_obra": 400.00
  }
  ```

| Campo              | Tipo    | Obrigatório? | Observação                         |
|--------------------|---------|--------------|-------------------------------------|
| ordem_servico      | número  | ✅ Sim       | ID da O.S. (relação 1-para-1)      |
| descricao_servico  | texto   | ✅ Sim       | O que foi feito                     |
| data_execucao      | data    | ✅ Sim       | Formato: `AAAA-MM-DD`              |
| custo_pecas        | decimal | ❌ Não       | Padrão: 0.00                        |
| custo_mao_de_obra  | decimal | ❌ Não       | Padrão: 0.00                        |

**Campo calculado**: O retorno incluirá `custo_total` (soma automática de peças + mão de obra).

---

## 📅 PARTE 12: Planos de Manutenção (Horímetro)

Aqui você configura a manutenção preditiva baseada nas horas de uso da máquina.

### 12.1 Listar Planos
- **Método**: `GET` | **URL**: `http://localhost:8000/api/planos-manutencao/`

### 12.2 Criar Plano de Manutenção
- **Método**: `POST` | **URL**: `http://localhost:8000/api/planos-manutencao/`
- **Body (JSON)**:
  ```json
  {
      "equipamento": 1,
      "nome_servico": "Troca de Óleo",
      "descricao": "Drenar e substituir óleo lubrificante 15W40.",
      "intervalo_horas": 100.0,
      "prioridade": "medio",
      "ativo": true
  }
  ```

| Campo           | Tipo    | Obrigatório? | Observação                                      |
|-----------------|---------|--------------|-------------------------------------------------|
| equipamento     | número  | ✅ Sim       | ID do equipamento                               |
| nome_servico    | texto   | ✅ Sim       | Ex: "Limpeza de Filtros"                       |
| descricao       | texto   | ✅ Sim       |                                                 |
| intervalo_horas | decimal | ✅ Sim       | Intervalo entre manutenções (ex: 500)           |
| prioridade      | texto   | ❌ Não       | `baixo`, `medio` ou `critico`                   |
| ativo           | bool    | ❌ Não       | Se o plano está rodando (padrão: `true`)        |

**A Lógica de Ouro (Como o disparo funciona na prática)**:

A manutenção preditiva por horímetro opera em **dois passos separados** para garantir máxima flexibilidade (uma máquina pode ter 5 planos diferentes rolando ao mesmo tempo).

**Passo a Passo do Teste Perfeito:**

1. **O Ponto de Partida**: Imagine que você tem um motor operando e ele já acumula **500 horas** de uso (`horimetro: 500` no equipamento).
2. **Criando o Plano**: Você cria um plano (POST acima) de "Troca de Óleo" com `intervalo_horas: 100`.
3. **O Carimbo Oculto**: No exato milissegundo em que você cria o plano, o sistema "olha" para o motor e grava: *"A última manutenção (fictícia) foi em 500h"* (`horimetro_ultima_os: 500`).
4. **O Alvo**: O sistema calcula internamente o próximo disparo: `500 + 100 = 600h`.
5. **A Mágica Acontece**: Algum tempo depois, o técnico (ou o sistema do painel) atualiza o horímetro do equipamento via `PATCH /api/equipamentos/{id}/` para **605h**.
   - O sistema intercepta o PATCH e detecta: `605 >= 600` (O limite do plano foi cruzado!).
   - **Gera a O.S. automaticamente** com `tipo_os: "preditiva"` e título `[PREDITIVA] Troca de Óleo`.
   - Atualiza o registro do plano: O novo "carimbo" (`horimetro_ultima_os`) passa a ser **605h**.
6. **O Novo Alvo**: O próximo disparo projetado agora será: `605 + 100 = 705h`.

**Sistemas Anti-Falhas Incluídos:**
- **Anti-Duplicação**: Se o horímetro continuar subindo (ex: para 610h) antes do técnico fechar a O.S. gerada, o sistema **NÃO** vai criar outra O.S. igual. Ele espera o ciclo ser finalizado.
- **Isolamento**: Se a máquina tem um plano para 100h e outro para 1000h, o sistema processa cada um de forma completamente independente.

**Como Testar:**
1. Crie o equipamento (Parte 5). Anote o ID e o horímetro inicial.
2. Crie o Plano de Manutenção (Parte 12.2) apontando para o ID do equipamento.
3. Faça um `PATCH` no Equipamento, aumentando o horímetro para um valor acima do intervalo.
4. Faça um `GET /api/ordens-servico/` e veja a O.S. preditiva lá, prontinha para o técnico assumir!


---

## 📊 PARTE 12: Dashboard e KPIs

### 12.1 Resumo Geral da Empresa
- **Método**: `GET` | **URL**: `http://localhost:8000/api/dashboards/resumo/`
- **Filtros opcionais**:
  - `?dias=30` → KPIs dos últimos 30 dias.
  - `?empresa_id=1` → (Apenas Admin) filtra por empresa.
- **Retorno**: Resumo com MTTR, MTBF, Disponibilidade, custos, alertas ativos e O.S. abertas.

### 12.2 KPIs por Equipamento
- **Método**: `GET` | **URL**: `http://localhost:8000/api/dashboards/kpis/`
- **Filtros**: `?equipamento_id=1` ou `?dias=30`

---

## 📝 PARTE 13: Checklist Completo de Auditoria

Use esta lista para garantir que testou tudo:

| #  | Teste                                        | Método | Endpoint                     | Esperado |
|----|----------------------------------------------|--------|------------------------------|----------|
| 1  | Login com credenciais corretas               | POST   | /api/auth/token/             | 200      |
| 2  | Login com senha errada                       | POST   | /api/auth/token/             | 401      |
| 3  | Acessar endpoint sem token                   | GET    | /api/equipamentos/           | 401      |
| 4  | Criar empresa com CNPJ duplicado             | POST   | /api/empresas/               | 400      |
| 5  | Técnico tenta criar equipamento              | POST   | /api/equipamentos/           | 403      |
| 6  | Técnico tenta acessar empresas               | GET    | /api/empresas/               | 403      |
| 7  | Enviar telemetria com texto em vez de número  | POST   | /api/telemetria/leituras/    | 400      |
| 8  | Enviar valor crítico e verificar O.S. gerada | POST   | /api/telemetria/leituras/    | 201      |
| 9  | Verificar alerta gerado automaticamente      | GET    | /api/alertas/                | 200      |
| 10 | Verificar O.S. gerada automaticamente        | GET    | /api/ordens-servico/         | 200      |
| 11 | Técnico B tenta ver O.S. do Técnico A        | GET    | /api/ordens-servico/         | (vazio)  |
| 12 | Concluir O.S. e verificar data_conclusao     | PATCH  | /api/ordens-servico/{id}/    | 200      |

---

## 💡 Dicas Finais

1. **Token expirou?** Faça o login novamente e atualize o token na Collection.
2. **Quer ver os campos de um endpoint?** Use o Swagger (`/api/schema/swagger-ui/`).
3. **Sempre confirme**: Após cada `POST`, faça um `GET` para verificar se o dado realmente foi salvo.
4. **IDs são importantes**: Anote o `id` de cada objeto que criar — você vai precisar dele para vincular sensores, leituras e O.S.
5. **Teste como diferentes perfis**: Faça login como `admin`, `gestor` e `tecnico` para ver como as permissões mudam.

---
*Parabéns! Você agora domina todos os endpoints da Plataforma de Manutenção Industrial.* 🏭
