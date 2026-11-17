const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');

function fixture(handler = () => ({})) {
  let app;
  const requests = [];
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8'), {
    Vue: { ref: value => ({ value }), reactive: value => value,
      computed: getter => ({ get value() { return getter(); } }), watch() {}, onMounted() {}, onUnmounted() {},
      nextTick: callback => callback?.(), createApp: options => ({ mount() { app = options.setup(); } }) },
    localStorage: { getItem: () => '', setItem() {}, removeItem() {} },
    document: { hidden: false, documentElement: { classList: { add() {}, remove() {} } }, getElementById() {} },
    window: { clearTimeout() {} }, console, URLSearchParams, Date,
    setTimeout: () => 1, clearTimeout() {}, setInterval: () => 1, clearInterval() {},
    fetch: async url => {
      requests.push(url);
      const data = await handler(new URL(url));
      return { ok: true, status: 200, headers: { get: () => 'application/json' }, text: async () => JSON.stringify(data) };
    },
  });
  app.me.value = { id: 1, tipo_usuario: 'admin' };
  return { app, requests };
}

const equipments = [
  { id: 1, nome: 'Prensa 10', empresa: 1, status: 'ativo' },
  { id: 2, nome: 'Prensa 2', empresa: 1, status: 'manutencao' },
  { id: 3, nome: 'Bomba hidráulica', empresa: 2, status: 'inativo' },
];
function paginated(url) {
  if (url.pathname.includes('/empresas/')) return [{ id: 1, nome: 'Unidade Norte' }, { id: 2, nome: 'Unidade Sul' }];
  if (url.pathname.includes('/equipamentos/')) return { results: equipments.slice(0, 1), next: '/api/equipamentos/?offset=1' };
  if (url.searchParams.has('offset')) return { results: [{ id: 2, equipamento: 2, setor: ' produção ' }, { id: 3, equipamento: 3, setor: 'Produção' }] };
  return { results: [{ id: 1, equipamento: 1, setor: 'Produção' }], next: 'http://127.0.0.1:9000/api/localizacao/?offset=1' };
}
function data(url) {
  if (url.pathname.includes('/equipamentos/') && url.searchParams.has('offset')) return { results: equipments.slice(1) };
  return paginated(url);
}

test('reúne todas as páginas, normaliza o setor e separa empresas com o mesmo setor', async () => {
  const { app, requests } = fixture(data);
  await app.fetchLocalizacoes();
  assert.equal(app.locationGroups.value.length, 2);
  assert.equal(app.locationEquipmentCount.value, 3);
  assert.deepEqual(Array.from(app.locationGroups.value[0].items, row => row.name), ['Prensa 2', 'Prensa 10']);
  assert.equal(app.locationGroups.value[1].company, 'Unidade Sul');
  assert.equal(app.locationGroups.value[0].items[0].status, 'manutencao');
  assert.equal(requests.length, 5);
  assert.equal(app.lists.localizacoes.length, 3);
});

test('busca por nome sem acentos, código e setor e seleciona o setor encontrado', async () => {
  const { app } = fixture(data);
  await app.fetchLocalizacoes();
  app.filters.localizacoes.search = 'hidraulica';
  assert.equal(app.locationEquipmentCount.value, 1);
  assert.equal(app.filteredLocationGroups.value[0].items[0].equipamento, 3);
  app.filters.localizacoes.search = '2';
  assert.equal(app.locationEquipmentCount.value, 1);
  app.filters.localizacoes.search = 'producao';
  assert.equal(app.locationEquipmentCount.value, 3);
  app.selectLocationSector(app.locationGroups.value[1].key);
  assert.equal(app.selectedLocationGroup.value.items.length, 1);
  assert.equal(app.locationEquipmentRows.value[0].equipamento, 3);
  app.clearLocationFilters();
  assert.equal(app.locationEquipmentCount.value, 3);
});

test('mostra apenas os equipamentos do setor selecionado, com seleção inicial automática', async () => {
  const { app } = fixture(data);
  await app.fetchLocalizacoes();
  const [first, second] = app.locationGroups.value;
  assert.equal(app.selectedLocationGroup.value.key, first.key);
  assert.deepEqual(Array.from(app.locationEquipmentRows.value, row => row.equipamento), [2, 1]);
  app.selectLocationSector(second.key);
  assert.deepEqual(Array.from(app.locationEquipmentRows.value, row => row.equipamento), [3]);
  assert.equal(app.locationEquipmentCount.value, 3);
});

function manyLocations(app) {
  app.locationState.rows = Array.from({ length: 29 }, (_, index) => ({
    id: index + 1, equipamento: index + 1, name: `Equipamento ${index + 1}`,
    setor: index < 11 ? 'Setor 1' : `Setor ${Math.floor((index - 11) / 3) + 2}`,
    companyId: 1, company: 'Unidade Norte', status: 'ativo',
  }));
}

test('limita a tela a cinco setores e quatro equipamentos sem perder itens entre páginas', () => {
  const { app } = fixture();
  manyLocations(app);
  assert.equal(app.locationSectorRows.value.length, 5);
  assert.equal(app.locationSectorPageCount.value, 2);
  assert.equal(app.locationEquipmentPageCount.value, 3);
  const seen = [];
  for (let page = 1; page <= 3; page++) {
    app.changeLocationEquipmentPage(page);
    assert.ok(app.locationEquipmentRows.value.length <= 4);
    seen.push(...Array.from(app.locationEquipmentRows.value, row => row.equipamento));
  }
  assert.deepEqual(seen, Array.from({ length: 11 }, (_, index) => index + 1));
  app.changeLocationSectorPage(2);
  assert.equal(app.locationSectorRows.value.length, 2);
  assert.equal(app.selectedLocationGroup.value.sector, 'Setor 6');
  assert.equal(app.locationEquipmentPage.value, 1);
  app.changeLocationSectorPage(1);
  assert.equal(app.selectedLocationGroup.value.sector, 'Setor 1');
});

test('busca encontra equipamento fora da página e reinicia a navegação sem esconder resultados', () => {
  const { app } = fixture();
  manyLocations(app);
  app.changeLocationEquipmentPage(3);
  app.filters.localizacoes.search = 'Equipamento 29';
  app.applyLocationSearch();
  assert.equal(app.selectedLocationGroup.value.sector, 'Setor 7');
  assert.equal(app.locationEquipmentRows.value[0].equipamento, 29);
  assert.equal(app.locationSectorPage.value, 1);
  assert.equal(app.locationEquipmentPage.value, 1);
  app.clearLocationFilters();
  assert.equal(app.locationEquipmentCount.value, 29);
  app.selectLocationSector(app.locationGroups.value[6].key);
  assert.equal(app.locationSectorPage.value, 2);
  assert.equal(app.selectedLocationGroup.value.sector, 'Setor 7');
});

test('atualizar dados após remover itens mantém a página válida e substitui setor removido', () => {
  const { app } = fixture();
  manyLocations(app);
  app.changeLocationEquipmentPage(3);
  app.locationState.rows = app.locationState.rows.filter(row => row.id > 8);
  assert.equal(app.locationEquipmentPage.value, 1);
  assert.equal(app.locationEquipmentRows.value.length, 3);
  app.selectLocationSector(app.locationGroups.value[6].key);
  app.locationState.rows = app.locationState.rows.filter(row => row.setor === 'Setor 2');
  assert.equal(app.locationSectorPage.value, 1);
  assert.equal(app.selectedLocationGroup.value.sector, 'Setor 2');
  app.locationState.rows = [];
  assert.equal(app.selectedLocationGroup.value, null);
  assert.equal(app.locationEquipmentRows.value.length, 0);
});

test('respeita o filtro global de empresa sem depender do filtro da API de localizações', async () => {
  // O endpoint de equipamentos aplica o escopo; localizações retorna ambas as empresas.
  const scoped = fixture(url => url.pathname.includes('/equipamentos/') ? [equipments[2]] : data(url));
  scoped.app.globalEmpresa.value = '2';
  await scoped.app.fetchLocalizacoes();
  assert.equal(scoped.app.locationEquipmentCount.value, 1);
  assert.equal(scoped.app.locationGroups.value[0].company, 'Unidade Sul');
  assert.ok(scoped.requests.some(url => url.includes('empresa=2')));
});

test('falha de carregamento oferece erro e não apresenta grupos parciais', async () => {
  const { app } = fixture(() => { throw new Error('offline'); });
  await app.fetchLocalizacoes();
  assert.equal(app.locationState.busy, false);
  assert.match(app.locationState.error, /Não foi possível/);
  assert.equal(app.locationGroups.value.length, 0);
});

test('resposta antiga não substitui recarga recente nem repovoa dados após logout', async () => {
  const releases = [];
  let delayed = true;
  const { app } = fixture(url => delayed && url.pathname.includes('/localizacao/')
    ? new Promise(resolve => releases.push(resolve)) : data(url));
  const pending = app.fetchLocalizacoes();
  delayed = false;
  await app.fetchLocalizacoes();
  releases[0]([{ id: 99, equipamento: 1, setor: 'Antigo' }]);
  await pending;
  assert.equal(app.locationEquipmentCount.value, 3);
  delayed = true;
  const logoutPending = app.fetchLocalizacoes();
  app.logout();
  releases[1]([{ id: 99, equipamento: 1, setor: 'Antigo' }]);
  await logoutPending;
  assert.equal(app.locationEquipmentCount.value, 0);
});
