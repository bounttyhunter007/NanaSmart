# FrontEnd - Plataforma de Manutenção Web

Este é o repositório do FrontEnd da Plataforma de Manutenção Web, desenvolvido utilizando **Vue.js**, uma ferramenta moderna de criação de interfaces web.

## Como iniciar o projeto (Guia para Iniciantes)

Para que o site funcione na sua máquina, assumimos que **a API (Backend em Python/Django) já esteja rodando** em outro terminal. Siga os passos abaixo para iniciar a interface visual (Front-End):

### Pré-requisitos
1. Você precisa ter o [Node.js](https://nodejs.org/) instalado no seu computador.
2. Certifique-se de estar dentro da pasta `FrontEnd` no terminal do seu computador.
   ```bash
   cd FrontEnd
   ```

### Passo 1: Instalar as dependências
Caso seja a primeira vez que você está abrindo o projeto em uma nova máquina ou caso novos pacotes tenham sido adicionados, é necessário baixar os arquivos auxiliares para o funcionamento do Vue.js. Para isso, rode o comando abaixo no terminal:
```bash
npm install
```
*(Você precisa de internet apenas para baixar essas dependências na primeira vez. Depois será tudo offline).*

### Passo 2: Rodar o site localmente
Agora é só ativar o servidor de desenvolvimento para visualizar as páginas. Rode:
```bash
npm run dev
```

Após rodar o comando, o terminal mostrará um link (geralmente `http://localhost:5173/`). Você pode clicar nesse link segurando a tecla **Ctrl** (ou copiar e colar no seu navegador) para abrir no navegador!

---

## 🗺️ Roadmap de Desenvolvimento (Tasks Iterativas)

Para otimizar nossa interação e focar em entregas modulares, organizamos o desenvolvimento em pequenas *Tasks*. Trabalharemos funcionalidade por funcionalidade, de forma inteligente, para você ver o sistema ganhando vida rapidamente!

### ✅ Task 0: Setup Inicial (Concluída)
- [x] Criação e configuração da estrutura base (Vite + Vue.js).
- [x] Isolamento da pasta FrontEnd e dependências (`package.json`, `node_modules`).
- [x] Arquivo `.gitignore` limpo e arquivo `README.md` orientativo.

### ✅ Task 1: Fundação do App (Concluída)
- [x] Limpeza dos arquivos nativos e de rascunhos originais do Vite.
- [x] Instalação e configuração do Roteador (`vue-router`) e Cliente HTTP (`axios`).
- [x] Construção do "esqueleto" geral: Barra Superior (Header) e Menu Lateral (Sidebar) fixos.


### ✅ Task 2: O Portão de Entrada (Login e Autenticação) (Concluída)
- [x] Criação da interface limpa e intuitiva de Autenticação (Login).
- [x] Conexão da tela à API Django para negociar o e receber o Token JWT de acesso.
- [x] Criação de "Guardas de Rota": Impedir acesso ou visualizar o portal sem ter se logado corretamente.

### ✅ Task 3: Gestão de Ativos (Equipamentos) (Concluída)
- [x] Criação da página de `Ativos`.
- [x] Listagem de equipamentos, permitindo visualizar os detalhes técnicos (ex: motor, esteira).
- [x] Interface para cadastrar novos equipamentos monitorados.
- <small>*(Melhoria Mapeada: Ações de Criação protegidas apenas para cargo de Admin na interface e API).*</small>

### ✅ Task 4: Monitoramento e Telemetria (Concluída)
- [x] Criação do painel de `Telemetria em Tempo Real`.
- [x] Integração com os sensores virtuais dos ativos (temperatura, vibração, rotação).
- [x] Indicadores visuais: Cores para leitura normal e estilos de advertência caso os índices subam muito.
- <small>*(Melhoria UX Efetuada: Consolidação Inteligente -> Os sensores foram agrupados dentro de Cards de Equipamentos, centralizando toda informação do ativo no mesmo espaço em vez de espalhar).*</small>

### ✅ Task 5: Central de Alertas (Concluída)
- [x] Página de visualização de `Alertas`.
- [x] Tabela interativa para listar todos os gatilhos gerados quando a telemetria sai do padrão.
- [x] Mecanismo de resolução rápida (botão para marcar como resolvido via API).
- <small>*(Nota Técnica: Os botões de "Abrir Painel Completo" nas outras telas serão funcionais nas Tasks 7 e 8).*</small>

### ✅ Task 6: Ordens de Manutenção (O.S) (Concluída)
- [x] Interface focada no painel de `Manutenções / O.S`.
- [x] Fluxo para que os operadores possam converter um alerta severo em uma Ordem de Manutenção.
- [x] Acompanhar status da O.S (Pendente, Em Execução, Concluída).
- <small>*(Integração: Alertas críticos agora possuem atalho direto para abertura de O.S com preenchimento automático).*</small>

### ✅ Task 7: Visão Executiva (Dashboard Principal) (Concluída)
- [x] Construção da `Tela Home` compilando o resumo completo da operação da empresa.
- [x] Captura das métricas gerenciais em um só local (Ativos ativos vs Parados, Alertas das últimas 24h).
- [x] Implementação de Gráficos ricos (Chart.js) mostrando a disponibilidade e status da frota.
- <small>*(KPIs: MTTR, MTBF e Disponibilidade calculados automaticamente por equipamento).*</small>

### 🚀 Task 8: Acabamento Premium e "Efeito UAU" (Polish Final)
- [ ] Revisão geral do Design: aplicar sombras densas, cores vibrantes, bordas modernas e "Glassmorphism".
- [ ] Adicionar micro-interações como Feedback visual nos botões (spinners de carregamento) e Toasts pop-ups ao dar erro ou sucesso.
- [ ] Teste extensivo da Responsividade para telas menores e tablets antes de lançar.
