const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');

function fixture(handler) {
  let app;
  const requests = [];
  const context = {
    Vue: { ref: value => ({ value }), reactive: value => value,
      computed: getter => ({ get value() { return getter(); } }), watch() {}, onMounted() {}, onUnmounted() {},
      nextTick: callback => callback?.(), createApp: options => ({ mount() { app = options.setup(); } }) },
    localStorage: { getItem: () => '', setItem() {}, removeItem() {} },
    document: { hidden: false, documentElement: { classList: { add() {}, remove() {} } }, getElementById() {} },
    window: { clearTimeout() {} }, console, URLSearchParams, Date, confirm: () => true,
    setTimeout: () => 1, clearTimeout() {}, setInterval: () => 1, clearInterval() {},
    fetch: async (url, options = {}) => {
      requests.push({ url, options });
      const data = await handler(url, options);
      const status = data?.httpStatus || 200;
      return { ok: status < 400, status, headers: { get: () => 'application/json' }, text: async () => JSON.stringify(data), json: async () => data };
    },
  };
  vm.runInNewContext(source, context);
  app.me.value = { id: 1, tipo_usuario: 'gestor', empresa: 2 };
  return { app, requests };
}
const config = (company, text = 'Padrão') => ({ empresa: company, effective_text: text, original_text: 'Padrão', is_customized: text !== 'Padrão' });
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};

test('abrir OS não gera análise; botão envia POST sem dados do navegador e evita clique duplicado', async () => {
  const pending = deferred();
  const { app, requests } = fixture(url => url.endsWith('/analise-ia/') ? pending.promise : { id: 10 });
  await app.openOrderDetails({ id: 10 });
  assert.equal(requests.length, 1);
  assert.equal(app.orderAnalysis.text, '');
  const running = app.analyzeOrder();
  await app.analyzeOrder();
  assert.equal(requests.length, 2);
  assert.equal(requests[1].options.method, 'POST');
  assert.equal(requests[1].options.body, undefined);
  assert.equal(app.orderAnalysis.busy, true);
  pending.resolve({ response: 'Resumo da ocorrência\nVerificar vedação.', model_used: 'teste' });
  await running;
  assert.equal(app.orderAnalysis.busy, false);
  assert.match(app.orderAnalysis.text, /Verificar vedação/);
  app.closeOrderDetails();
  await app.openOrderDetails({ id: 10 });
  assert.equal(app.orderAnalysis.text, '');
});

test('respostas atrasadas são descartadas ao fechar, reabrir ou trocar a OS', async () => {
  for (const nextId of [null, 10, 20]) {
    const pending = deferred();
    const { app } = fixture(url => url.endsWith('/analise-ia/') ? pending.promise : { id: Number(url.split('/').at(-2)) });
    await app.openOrderDetails({ id: 10 });
    const running = app.analyzeOrder();
    app.closeOrderDetails();
    if (nextId) await app.openOrderDetails({ id: nextId });
    pending.resolve({ response: 'Resposta antiga' });
    await running;
    assert.equal(app.orderAnalysis.text, '');
    assert.equal(app.orderAnalysis.busy, false);
  }
});

test('resposta é descartada após mudança de empresa ou usuário', async () => {
  for (const change of [app => { app.globalEmpresa.value = 3; }, app => { app.me.value = { id: 7 }; }]) {
    const pending = deferred();
    const { app } = fixture(url => url.endsWith('/analise-ia/') ? pending.promise : { id: 10 });
    await app.openOrderDetails({ id: 10 });
    const running = app.analyzeOrder();
    change(app);
    pending.resolve({ response: 'Resposta de outro contexto' });
    await running;
    assert.equal(app.orderAnalysis.text, '');
  }
});

test('falha ou resposta vazia aparece como erro e permite tentar novamente', async () => {
  let attempts = 0;
  const { app } = fixture(url => {
    if (!url.endsWith('/analise-ia/')) return { id: 10 };
    if (++attempts === 1) throw new Error('Sem conexão');
    return attempts === 2 ? { response: '  ' } : { response: 'Análise válida' };
  });
  await app.openOrderDetails({ id: 10 });
  for (let index = 0; index < 2; index++) {
    await app.analyzeOrder();
    assert.ok(app.orderAnalysis.error);
    assert.equal(app.orderAnalysis.text, '');
    assert.equal(app.orderAnalysis.busy, false);
  }
  await app.analyzeOrder();
  assert.equal(app.orderAnalysis.error, '');
  assert.equal(app.orderAnalysis.text, 'Análise válida');
});

test('editor carrega somente instruções da empresa; salva e restaura sem carregar prompts globais', async () => {
  const { app, requests } = fixture((url, options) => config(2,
    options.method === 'PATCH' ? JSON.parse(options.body).custom_text : 'Padrão'));
  await app.fetchPrompts();
  assert.equal(requests.length, 1);
  assert.match(requests[0].url, /analise-os\/\?empresa=2$/);
  assert.equal(app.osPrompt.edit_text, 'Padrão');
  app.osPrompt.edit_text = 'Verifique vazamentos';
  await app.saveOsPrompt();
  assert.equal(app.osPrompt.edit_text, 'Verifique vazamentos');
  assert.equal(app.osPrompt.is_customized, true);
  await app.saveOsPrompt(true);
  assert.match(requests.at(-1).url, /analise-os\/reset\/\?empresa=2$/);
  assert.equal(app.osPrompt.edit_text, 'Padrão');
  assert.equal(app.osPrompt.is_customized, false);
});

test('erro HTTP do provedor aparece como mensagem sem preencher o resultado', async () => {
  const { app } = fixture(url => url.endsWith('/analise-ia/')
    ? { httpStatus: 503, detail: 'A análise por IA está indisponível.' } : { id: 10 });
  await app.openOrderDetails({ id: 10 });
  await app.analyzeOrder();
  assert.equal(app.orderAnalysis.error, 'A análise por IA está indisponível.');
  assert.equal(app.orderAnalysis.text, '');
  assert.equal(app.orderAnalysis.busy, false);
});

test('alterar uma OS aberta descarta a análise do estado anterior', async () => {
  const { app } = fixture(url => {
    if (url.endsWith('/analise-ia/')) return { response: 'Avaliação anterior' };
    if (url.endsWith('/10/')) return { id: 10, responsavel: null, status: 'pendente' };
    return { count: 0, results: [] };
  });
  await app.openOrderDetails({ id: 10 });
  await app.analyzeOrder();
  assert.equal(app.orderAnalysis.text, 'Avaliação anterior');
  await app.assumirOS(app.orderDetail.order);
  assert.equal(app.orderAnalysis.text, '');
});

test('técnico não acessa editor; administrador precisa selecionar uma empresa', async () => {
  const { app, requests } = fixture(() => config(3));
  app.me.value.tipo_usuario = 'tecnico';
  app.navigate('prompts');
  assert.equal(app.view.value, 'dashboard');
  await app.fetchPrompts();
  await app.saveOsPrompt();
  assert.equal(requests.length, 0);
  app.me.value.tipo_usuario = 'admin';
  await app.fetchPrompts();
  assert.equal(requests.length, 0);
  app.globalEmpresa.value = 3;
  await app.fetchPrompts();
  assert.equal(requests.length, 1);
  assert.match(requests[0].url, /empresa=3$/);
});

test('editor descarta carregamento ou salvamento atrasado de outra empresa', async () => {
  for (const saving of [false, true]) {
    const pending = deferred();
    const { app } = fixture((url, options) => url.endsWith('empresa=2') && (!saving || options.method === 'PATCH')
      ? pending.promise : config(url.endsWith('empresa=3') ? 3 : 2));
    app.me.value.tipo_usuario = 'admin'; app.globalEmpresa.value = 2;
    let running;
    if (saving) {
      await app.fetchPrompts();
      app.osPrompt.edit_text = 'Personalização de A';
      running = app.saveOsPrompt();
    } else running = app.fetchPrompts();
    app.globalEmpresa.value = 3;
    await app.fetchPrompts();
    pending.resolve(config(2, 'Resposta antiga de A'));
    await running;
    assert.equal(app.osPrompt.edit_text, 'Padrão');
    assert.equal(app.osPrompt.busy, false);
    assert.equal(app.osPrompt.saving, false);
  }
});

test('salvar o texto padrão remove a personalização em vez de congelar uma cópia', async () => {
  const { app, requests } = fixture(() => config(2));
  await app.fetchPrompts();
  await app.saveOsPrompt();
  assert.equal(JSON.parse(requests.at(-1).options.body).custom_text, '');
});
