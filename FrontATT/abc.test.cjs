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
      return { ok: true, status: 200, headers: { get: () => 'application/json' }, json: async () => data };
    },
  };
  vm.runInNewContext(source, context);
  app.me.value = { id: 1, tipo_usuario: 'gestor', empresa: 2 };
  return { app, requests };
}

test('fila usa filtros no servidor, preserva ordenação recebida e paginação completa', async () => {
  const next = 'http://127.0.0.1:9000/api/ordens-servico/?prioridade=A&limit=2&offset=2';
  const { app, requests } = fixture(url => new URL(url).searchParams.has('offset')
    ? { count: 3, results: [{ id: 3, prioridade: 'A' }], next: null, previous: 'prev', total_escopo: 8, a_definir: 0 }
    : { count: 3, results: [{ id: 1, prioridade: 'B' }, { id: 2, prioridade: 'A' }], next, total_escopo: 8, a_definir: 1 });
  app.globalEmpresa.value = 2;
  app.filters.ordens.responsavel_escopo = 'livres';
  await app.selectOrderPriority('A');
  const query = new URL(requests[0].url).searchParams;
  assert.equal(query.get('prioridade'), 'A');
  assert.equal(query.get('abertas'), 'true');
  assert.equal(query.get('responsavel_escopo'), 'livres');
  assert.equal(query.get('equipamento__empresa'), '2');
  assert.deepEqual(Array.from(app.lists.ordens, row => row.id), [1, 2]);
  assert.equal(app.orderState.count, 3);
  assert.equal(app.orderState.total, 8);
  await app.fetchPage('ordens', app.pages.ordens.next);
  assert.equal(app.lists.ordens[0].id, 3);
  assert.equal(new URL(requests[1].url).searchParams.get('offset'), '2');
});

test('filtro A definir é independente de C e limpeza retorna à fila aberta', async () => {
  const { app, requests } = fixture(() => ({ count: 0, results: [], total_escopo: 5 }));
  await app.selectOrderPriority('a_definir');
  assert.equal(new URL(requests[0].url).searchParams.get('prioridade'), 'a_definir');
  app.filters.ordens.status = 'concluida'; app.filters.ordens.search = 'motor';
  await app.clearOrderFilters();
  assert.equal(app.filters.ordens.status, 'abertas');
  assert.equal(app.filters.ordens.prioridade, '');
  assert.equal(app.orderState.total, 5);
});

test('resposta antiga não substitui filtro novo nem repovoa a fila após logout', async () => {
  let release;
  const { app } = fixture(url => url.includes('prioridade=A') ? new Promise(resolve => { release = resolve; }) : { count: 1, results: [{ id: 2 }], total_escopo: 2 });
  const old = app.selectOrderPriority('A');
  await app.selectOrderPriority('B');
  release({ count: 1, results: [{ id: 1 }] }); await old;
  assert.equal(app.lists.ordens[0].id, 2);
  const pending = app.selectOrderPriority('A');
  app.logout();
  release({ count: 1, results: [{ id: 1 }] }); await pending;
  assert.equal(app.lists.ordens.length, 0);
});

test('criação e edição gerais não enviam prioridade nem metadados de herança', async () => {
  const { app, requests } = fixture((url, options) => {
    if (url.includes('/equipamentos/')) return { results: [{ id: 5, empresa: 2, nome: 'Bomba', criticidade: 'B' }] };
    if (url.includes('/empresas/')) return { results: [{ id: 2, nome: 'Empresa' }] };
    if (options.method === 'POST' || options.method === 'PUT') return { id: 9 };
    return { results: [], count: 0 };
  });
  app.view.value = 'ordens';
  await app.openModal('ordem');
  assert.equal(app.fd.prioridade, undefined);
  Object.assign(app.fd, { titulo: 'Inspeção', descricao: 'Inspecionar', equipamento: 5 });
  await app.saveItem();
  await app.editItem('ordem', { id: 9, titulo: 'Inspeção', descricao: 'Inspecionar', equipamento: 5, prioridade: 'B', prioridade_automatica: 'B', prioridade_origem: 'herdada' });
  await app.saveItem();
  const writes = requests.filter(r => ['POST', 'PUT'].includes(r.options.method));
  assert.equal(writes.length, 2);
  for (const write of writes) {
    const payload = JSON.parse(write.options.body);
    assert.equal('prioridade' in payload, false);
    assert.equal('prioridade_automatica' in payload, false);
    assert.equal('prioridade_origem' in payload, false);
  }
});

test('consulta de critérios não publica e publicação envia validação da empresa', async () => {
  const { app, requests } = fixture((url, options) => {
    if (url.includes('/empresas/')) return { results: [{ id: 2, nome: 'Empresa' }] };
    return { empresa: 2, revisao: options.method === 'POST' ? 1 : null, criterio_a: 'Alto', criterio_b: 'Médio', criterio_c: 'Baixo' };
  });
  await app.openCriteria(2);
  assert.equal(requests.some(r => r.options.method === 'POST'), false);
  Object.assign(app.criteriaModal.data, { representante_manutencao: 'Representante', data_validacao: '2026-11-06' });
  await app.saveCriteria();
  const payload = JSON.parse(requests.find(r => r.options.method === 'POST').options.body);
  assert.equal(payload.empresa, 2);
  assert.equal(payload.representante_manutencao, 'Representante');
  assert.equal(payload.revisao, undefined);
});

test('tipo apenas sugere até aceitação explícita', async () => {
  const { app } = fixture(() => ({}));
  app.equipmentGuide.types = [{ id: 3, criticidade_padrao: 'B' }];
  Object.assign(app.fd, { tipo_equipamento: 3, criticidade: null, aceitar_sugestao: false });
  assert.equal(app.fd.criticidade, null);
  app.acceptEquipmentSuggestion();
  assert.equal(app.fd.criticidade, 'B');
  assert.equal(app.fd.aceitar_sugestao, true);
});

test('ajuste dedicado exige motivo e restauração não envia nova classe', async () => {
  const order = { id: 8, prioridade: 'B', prioridade_automatica: 'B', status: 'pendente' };
  const { app, requests } = fixture(url => url.includes('historico_prioridade') ? { results: [] } : order);
  await app.openPriority(order);
  await app.savePriority(false);
  assert.equal(requests.some(r => r.options.method === 'POST'), false);
  app.priorityModal.reason = 'Parada do processo.'; app.priorityModal.choice = 'A';
  await app.savePriority(false);
  const adjusted = requests.find(r => r.url.includes('ajustar_prioridade'));
  assert.equal(JSON.parse(adjusted.options.body).prioridade, 'A');
  app.priorityModal.reason = 'Restaurar planejamento.';
  await app.savePriority(true);
  const restored = requests.find(r => r.url.includes('restaurar_prioridade'));
  assert.deepEqual(JSON.parse(restored.options.body), { justificativa: 'Restaurar planejamento.' });
});

test('exportação envia o mesmo recorte da lista de OS', async () => {
  const { app, requests } = fixture(() => { throw Error('Download indisponível no teste'); });
  Object.assign(app.filters.ordens, { prioridade: 'B', search: 'motor', responsavel_escopo: 'livres', equipamento: 4, setor: 'Linha 1' });
  app.globalEmpresa.value = 2;
  await app.exportData('ordens-servico', 'csv');
  const query = new URL(requests[0].url).searchParams;
  assert.equal(query.toString(), app.orderParams().toString());
});

test('categorias nulas e registros legados têm rótulos explícitos', () => {
  const { app } = fixture(() => ({}));
  assert.equal(app.prioridadeLabel(null), 'A definir');
  assert.equal(app.criticidadeLabel(null), 'Não avaliada');
  assert.match(app.criticidadeLabel('D', true), /legado/);
  assert.match(app.historicPriorityLabel('critica'), /legado/);
});

test('resposta de ajuste após logout não reabre detalhes nem consulta outra sessão', async () => {
  let release;
  const order = { id: 8, prioridade: 'B', status: 'pendente' };
  const { app, requests } = fixture((url, options) => options.method === 'POST'
    ? new Promise(resolve => { release = resolve; })
    : url.includes('historico_prioridade') ? { results: [] } : order);
  await app.openPriority(order);
  app.priorityModal.reason = 'Antecipar manutenção.';
  const saving = app.savePriority();
  app.logout();
  const count = requests.length;
  release({ ...order, prioridade: 'A' }); await saving;
  assert.equal(app.priorityModal.open, false);
  assert.equal(app.priorityModal.order, null);
  assert.equal(requests.length, count);
});

test('resposta de publicação de critérios após logout não repovoa o formulário', async () => {
  let release;
  const { app } = fixture((url, options) => options.method === 'POST'
    ? new Promise(resolve => { release = resolve; })
    : url.includes('/empresas/') ? { results: [{ id: 2, nome: 'Empresa' }] } : { empresa: 2 });
  await app.openCriteria(2);
  const saving = app.saveCriteria();
  app.logout();
  release({ empresa: 2, revisao: 1 }); await saving;
  assert.equal(app.criteriaModal.open, false);
  assert.equal(Object.keys(app.criteriaModal.data).length, 0);
});
