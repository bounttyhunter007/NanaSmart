const { createApp, ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } = Vue;
const BASE = 'http://127.0.0.1:9000';

// Helper: ordena por nível de severidade (critica → alta → media → baixa)
const NIVEL_PRIORIDADE = { A: 0, B: 1, C: 2, critica: 0, alta: 1, media: 2, baixa: 3 };
function sortByNivel(items, campo = 'nivel') {
  return items.sort((a, b) => (NIVEL_PRIORIDADE[a[campo]] ?? 3) - (NIVEL_PRIORIDADE[b[campo]] ?? 3));
}

// Helper: ordena por tipo de usuário (admin → gestor → tecnico)
const TIPO_USUARIO_PRIORIDADE = { admin: 0, gestor: 1, tecnico: 2 };
function sortByTipoUsuario(items, campo = 'tipo_usuario') {
  return items.sort((a, b) => (TIPO_USUARIO_PRIORIDADE[a[campo]] ?? 3) - (TIPO_USUARIO_PRIORIDADE[b[campo]] ?? 3));
}

createApp({
  components: { LiveChart: globalThis.NanaLiveChart?.component, MeasurementSample: globalThis.NanaLiveChart?.sampleComponent },
  setup() {
    const token = ref(localStorage.getItem('sentinel_token') || '');
    const refreshTk = ref(localStorage.getItem('sentinel_refresh') || '');
    const me = ref(null);
    const view = ref('dashboard');
    const loading = ref(false);
    const loginLoading = ref(false);
    const loginError = ref('');
    const loginForm = reactive({ username: '', password: '' });
    const kpis = ref(null);
    const dashAlerts = ref([]);
    const dashAlertsCollapsed = ref(false);
    const dashOrdensCollapsed = ref(false);
    const alertCount = ref(0);
    const toasts = ref([]);
    const globalEmpresa = ref('');  // Filtro global por empresa (admin)

    // ─ Theme (dark/light) ───────────────────────
    const darkMode = ref(localStorage.getItem('nanasmart_theme') !== 'light');
    function applyTheme() {
      if (darkMode.value) {
        document.documentElement.classList.remove('light-mode');
      } else {
        document.documentElement.classList.add('light-mode');
      }
    }
    function toggleTheme() {
      darkMode.value = !darkMode.value;
      localStorage.setItem('nanasmart_theme', darkMode.value ? 'dark' : 'light');
      applyTheme();
    }
    // Aplica o tema salvo imediatamente
    applyTheme();

    // ─ Dashboard chart filters ──────────────────────
    const dashTelemetriaEquip = ref('');
    const dashTelemetriaSensor = ref('');
    const dashCustoSetor = ref('');
    const dashSetor = ref('');
    const dashEquipamento = ref('');
    const explainerCollapsed = ref(true);
    const dashboardKpis = ref([]);
    const dashboardSummary = ref(null);
    const dashboardKpisLoading = ref(false);
    const dashboardKpisError = ref(null);
    let dashboardSummaryRequest = 0;

    const lists = reactive({
      equipamentos: [], alertas: [], ordens: [],
      sensores: [], leituras: [], historico: [], empresas: [],
      usuarios: [], localizacoes: [], prompts: []
    });
    const trendMonitor = reactive({ busy: false, updatedAt: null, error: '', newCount: 0 });
    let trendPollTimer = null;
    let trendMonitorRequest = 0;
    let knownTrendConditions = null;
    function resetTrendMonitoring() {
      ++trendMonitorRequest; knownTrendConditions = null; trendAlerts.value = [];
      Object.assign(trendMonitor, { busy: false, updatedAt: null, error: '', newCount: 0 });
    }
    function stopTrendPolling() {
      if (trendPollTimer !== null) clearInterval(trendPollTimer);
      trendPollTimer = null;
    }
    function startTrendPolling() {
      stopTrendPolling();
      if (!token.value) return;
      trendPollTimer = setInterval(refreshTrendMonitoring, 30000);
    }
    const trendAlerts = ref([]); // Painel de tendências de risco
    const trendDataCache = reactive({}); // sensor_id -> dados de tendência + ai_analysis
    const trendAILoading = reactive({}); // sensor_id -> booleano
    const trendConfigModal = reactive({
      open: false, loading: false, saving: false,
      sensorId: '', equipamentoId: '',
      form: {},
      isGlobal: false, error: ''
    });
    const leiturasTodayCount = ref(0);
    const leiturasTotalCount = ref(0);
    const pages = reactive({
      equipamentos: { next: null, prev: null },
      alertas: { next: null, prev: null },
      ordens: { next: null, prev: null },
      historico: { next: null, prev: null },
      sensores: { next: null, prev: null },
      leituras: { next: null, prev: null },
      empresas: { next: null, prev: null },
      usuarios: { next: null, prev: null },
      localizacoes: { next: null, prev: null },
    });
    const filters = reactive({
      equipamentos: { search: '', status: '', empresa: '', setor: '' },
      alertas: { search: '', nivel: '', origem: '', equipamento: '', sensor: '', from: '', to: '', status: '', setor: '' },
      ordens: { search: '', status: 'abertas', prioridade: '', tipo_os: '', abertas: true, responsavel_escopo: '', equipamento: '', setor: '' },
      historico: { search: '', data_de: '', data_ate: '', custo_min: '', custo_max: '' },
      empresas: { search: '' },
      usuarios: { search: '' },
      localizacoes: { search: '', setor: '' },
    });

    // ─ Modal ─────────────────────────────────────────
    const modal = reactive({ open: false, type: '', title: '', editId: null, saving: false, oldStatus: null });
    const fd = reactive({});
    const formErrors = ref({});
    const alertHistory = reactive({ busy: false, count: 0, error: '', url: '', detail: null, detailBusy: false, detailError: '' });
    let alertRequest = 0;
    let alertDetailRequest = 0;
    const alertSensors = computed(() => telemetry.sensors.filter(sensor =>
      !filters.alertas.equipamento || Number(sensor.equipamento) === Number(filters.alertas.equipamento)));
    const alertEvidence = computed(() => alertHistory.detail?.dados_deteccao || {});
    const alertReadings = computed(() => alertEvidence.value.leituras || []);
    const alertThresholds = computed(() => {
      const limit = Number(alertEvidence.value.limite_operacional);
      if (alertEvidence.value.limite_operacional == null || !Number.isFinite(limit)) return [];
      const percentages = alertEvidence.value.analise?.limites_pct;
      return percentages ? ['baixo', 'medio', 'critico'].map(level => ({
        label: { baixo: 'Baixo', medio: 'Médio', critico: 'Crítico' }[level],
        value: limit * percentages[level] / 100, percent: percentages[level], color: nivelColor(level),
      })) : [{ label: 'Limite superior', value: limit, color: nivelColor('critico') }];
    });
    const alertChart = computed(() => {
      const readings = alertReadings.value;
      const chart = makeLineChart([...readings].reverse(), 640, 180, readings.length,
        alertThresholds.value.map(row => row.value));
      if (!readings.length) return { ...chart, thresholds: [] };
      const times = readings.map(row => new Date(row.timestamp).getTime());
      const duration = times[times.length - 1] - times[0];
      if (duration > 0 && times.every(Number.isFinite)) {
        chart.dots = chart.dots.map((point, index) => ({ ...point, x: (times[index] - times[0]) / duration * 640 }));
        chart.path = chart.dots.map((point, index) => `${index ? 'L' : 'M'}${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' ');
      }
      const range = chart.highValue - chart.lowValue || 1;
      chart.thresholds = alertThresholds.value.map(row => ({ ...row, y: 162 - (row.value - chart.lowValue) / range * 144 }));
      return chart;
    });

    const equipModal = reactive({
      open: false,
      equipamento: null,
      sensors: [],
      selectedSensor: null,
      readings: [],
      loading: false,
      refreshing: false,
      error: '',
      lastRefresh: null,
      ordens: [],
      osFilter: 'todas',
    });
    let equipModalPollTimer = null;

    const selectedEquipSensor = computed(() => {
      return equipModal.sensors.find(s => s.id === equipModal.selectedSensor) || null;
    });

    const selectedSensorLabel = computed(() => {
      if (!selectedEquipSensor.value) return 'sensor';
      return `${selectedEquipSensor.value.nome}${selectedEquipSensor.value.tipo ? ` (${selectedEquipSensor.value.tipo})` : ''}`;
    });

    const equipModalChart = computed(() => {
      return makeLineChart(equipModal.readings, 360, 180);
    });

    const equipModalStats = computed(() => {
      const values = equipModal.readings.map(r => parseFloat(r.valor) || 0);
      if (!values.length) return { min: '—', max: '—', last: '—', count: 0 };
      const last = values[0];
      return {
        min: Math.min(...values).toFixed(2),
        max: Math.max(...values).toFixed(2),
        last: last.toFixed(2),
        count: values.length,
      };
    });

    const equipModalFilteredOrdens = computed(() => {
      if (equipModal.osFilter === 'automaticas') return equipModal.ordens.filter(o => o.alerta_origem);
      if (equipModal.osFilter === 'manuais') return equipModal.ordens.filter(o => !o.alerta_origem);
      return equipModal.ordens;
    });

    // ─ Computed básicos ──────────────────────────────
    const isAdmin = computed(() => me.value?.tipo_usuario === 'admin');
    const isAdminOrGestor = computed(() => ['admin', 'gestor'].includes(me.value?.tipo_usuario));
    const isTecnico = computed(() => me.value?.tipo_usuario === 'tecnico');
    const osSemTecnicoCount = computed(() => lists.ordens.filter(o => !o.responsavel && o.status !== 'concluida' && o.status !== 'cancelada').length);
    
    const ordensFilaPrioridade = computed(() => lists.ordens);

    const userInitial = computed(() => (me.value?.username || 'U')[0].toUpperCase());
    const viewTitle = computed(() => ({
      dashboard: 'Dashboard', equipamentos: 'Equipamentos', alertas: 'Histórico de alertas',
      ordens: 'Ordens de Serviço', telemetria: 'Telemetria', tendencias: 'Tendências',
      historico: 'Histórico de Manutenção', empresas: 'Empresas',
      usuarios: 'Usuários', localizacoes: 'Localizações',
      perfil: 'Meu Perfil', prompts: 'Configurações de Prompts da IA'
    }[view.value] || ''));

    // ═══════════════════════════════════════════════
    //  DASHBOARD CHARTS
    // ═══════════════════════════════════════════════

    const chartEquipStatus = computed(() => {
      if (!isTecnico.value && dashboardSummary.value?.resumo_status) {
        const counts = dashboardSummary.value.resumo_status;
        return [
          { label: 'Ativo', value: counts.ativo || 0, color: '#00d4aa' },
          { label: 'Manutenção', value: counts.manutencao || 0, color: '#ffaa00' },
          { label: 'Inativo', value: counts.inativo || 0, color: '#ff3b3b' },
        ].filter(s => s.value > 0);
      }
      const eq = isTecnico.value ? dashboardEquipamentos.value : lists.equipamentos;
      if (!eq.length && kpis.value) {
        const op = kpis.value.equipamentos_operacionais ?? kpis.value.equipamentos_ativos ?? 0;
        const tot = kpis.value.total_equipamentos ?? 0;
        return [
          { label: 'Ativo', value: op, color: '#00d4aa' },
          { label: 'Inativo/Man', value: tot - op, color: '#ff3b3b' },
        ].filter(s => s.value > 0);
      }
      const counts = { ativo: 0, manutencao: 0, inativo: 0 };
      eq.forEach(e => { if (counts[e.status] !== undefined) counts[e.status]++; });
      return [
        { label: 'Ativo', value: counts.ativo, color: '#00d4aa' },
        { label: 'Manutenção', value: counts.manutencao, color: '#ffaa00' },
        { label: 'Inativo', value: counts.inativo, color: '#ff3b3b' },
      ].filter(s => s.value > 0);
    });

    const chartAlertNivel = computed(() => {
      const counts = dashboardSummary.value?.alertas_24h
        ? { ...dashboardSummary.value.alertas_24h }
        : { critico: 0, medio: 0, baixo: 0 };
      if (!dashboardSummary.value) {
        dashAlerts.value.forEach(a => { if (counts[a.nivel] !== undefined) counts[a.nivel]++; });
      }
      const max = Math.max(counts.critico, counts.medio, counts.baixo, 1);
      return [
        { label: 'Crítico', value: counts.critico, pct: (counts.critico / max) * 100, color: '#ff3b3b' },
        { label: 'Médio', value: counts.medio, pct: (counts.medio / max) * 100, color: '#ffaa00' },
        { label: 'Baixo', value: counts.baixo, pct: (counts.baixo / max) * 100, color: '#00d4aa' },
      ];
    });

    const chartOrdens = computed(() => {
      const counts = dashboardSummary.value?.resumo_ordens
        ? { ...dashboardSummary.value.resumo_ordens }
        : { pendente: 0, andamento: 0, concluida: 0, cancelada: 0 };
      if (!dashboardSummary.value) {
        lists.ordens.forEach(o => { if (counts[o.status] !== undefined) counts[o.status]++; });
      }
      const max = Math.max(...Object.values(counts), 1);
      return [
        { label: 'Pendente', value: counts.pendente, pct: (counts.pendente / max) * 100, color: '#4db8ff' },
        { label: 'Andamento', value: counts.andamento, pct: (counts.andamento / max) * 100, color: '#ffaa00' },
        { label: 'Concluída', value: counts.concluida, pct: (counts.concluida / max) * 100, color: '#00d4aa' },
        { label: 'Cancelada', value: counts.cancelada, pct: (counts.cancelada / max) * 100, color: '#374455' },
      ];
    });

    const performanceOpen = ref(false);
    const liveOpen = ref(false);
    const telemetryLiveOpen = ref(false);
    const dashboardTab = ref('minhas');
    const companySearch = ref('');
    const dashboardUpdatedAt = ref(null);
    let dashboardRequest = 0, dashboardTimer = null;
    const dashboardAdminOverview = computed(() => isAdmin.value && !globalEmpresa.value);
    const dashboardEquipamentos = computed(() => dashboardSummary.value?.opcoes_equipamentos || []);
    const dashboardEquipmentOptions = computed(() => dashboardEquipamentos.value.filter(e => !dashSetor.value || e.setor === dashSetor.value));
    const availableDashboardSectors = computed(() => dashboardSummary.value?.setores || []);
    const dashboardCompanies = computed(() => (dashboardSummary.value?.empresas || []).filter(c => c.nome.toLocaleLowerCase('pt-BR').includes(companySearch.value.trim().toLocaleLowerCase('pt-BR'))));
    const dashboardOrders = computed(() => {
      const d = dashboardSummary.value;
      return isTecnico.value ? (dashboardTab.value === 'minhas' ? d?.minhas_ordens_prioritarias : d?.ordens_disponiveis) || [] : d?.ordens_prioritarias || [];
    });
    const dashboardCards = computed(() => {
      const d = dashboardSummary.value;
      if (dashboardAdminOverview.value) return [
        { label: 'Empresas cadastradas', value: d?.total_empresas },
        { label: 'Empresas com alertas críticos', value: d?.empresas_com_alertas_criticos, critical: true },
        { label: 'Ordens abertas', value: d?.os_abertas },
        { label: 'Sem responsável', value: d?.ordens_sem_tecnico },
      ];
      if (isTecnico.value) return [
        { label: 'Minhas pendentes', value: d?.minhas_pendentes, action: 'pendente' },
        { label: 'Meus atendimentos', value: d?.minhas_em_andamento, action: 'andamento' },
        { label: 'Disponíveis para assumir', value: d?.ordens_sem_tecnico, action: 'livres' },
      ];
      return [
        { label: 'Alertas críticos ativos', value: d?.alertas_ativos?.critico, critical: true, action: 'alertas' },
        { label: 'Equipamentos em manutenção', value: d?.resumo_status?.manutencao, action: 'equipamentos' },
        { label: 'Ordens abertas', value: d?.os_abertas, action: 'abertas' },
        { label: 'Sem responsável', value: d?.ordens_sem_tecnico, action: 'livres' },
      ];
    });
    const dashboardMetrics = computed(() => dashboardSummary.value?.desempenho || {});
    const dashboardCostChart = computed(() => {
      const rows = (dashboardSummary.value?.custos_por_dia || []).map((d,i) => ({ id:i, valor:Number(d.pecas)+Number(d.mao_de_obra), timestamp:d.data_execucao+'T12:00:00' }));
      return globalThis.NanaLiveChart?.chart(rows, null) || { points:[], ticks:[], times:[] };
    });
    function metric(value, suffix = '') { return value == null ? 'Sem histórico suficiente' : new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 2 }).format(value) + suffix; }
    function dashboardCompany(id = '') { globalEmpresa.value = id; onGlobalEmpresaChange(); }
    function applyDashboardFilters() {
      if (!dashboardEquipmentOptions.value.some(e => Number(e.id) === Number(dashEquipamento.value))) dashEquipamento.value = '';
      fetchDashboard();
    }
    function togglePerformance(event) { performanceOpen.value = event.target.open; if (performanceOpen.value) fetchDashboard({ silent: true }); }
    function openDashboardOrders(scope = '') {
      Object.assign(filters.ordens, { search: '', status: ['pendente', 'andamento'].includes(scope) ? scope : 'abertas', prioridade: '', tipo_os: '', abertas: true,
        responsavel_escopo: scope === 'livres' ? 'livres' : isTecnico.value ? 'minhas' : '', equipamento: dashEquipamento.value, setor: dashSetor.value });
      return navigate('ordens');
    }
    async function openDashboardOrder(order) {
      return openOrderDetails(order);
    }
    function dashboardAction(action) {
      if (action === 'alertas') {
        Object.assign(filters.alertas, { search: '', nivel: 'critico', origem: '', equipamento: dashEquipamento.value, sensor: '', from: '', to: '', status: 'ativo', setor: dashSetor.value });
        return navigate('alertas');
      }
      if (action === 'equipamentos') {
        Object.assign(filters.equipamentos, { search: '', status: 'manutencao', empresa: '', setor: dashSetor.value });
        return navigate('equipamentos');
      }
      if (action) return openDashboardOrders(action);
    }
    function dashboardAllAlerts() {
      Object.assign(filters.alertas, { search: '', nivel: '', origem: '', equipamento: dashEquipamento.value, sensor: '', from: '', to: '', status: 'ativo', setor: dashSetor.value });
      return navigate('alertas');
    }

    function getEquipamentoId(item) {
      if (item == null) return null;
      return typeof item === 'object' ? item.id : item;
    }

    function buildTelemetriaUrl({ limit = 50, allowedEqIds = null, sensorId = null, equipamentoId = null, timestampDe = null, timestampAte = null } = {}) {
      const params = new URLSearchParams();
      params.set('limit', String(limit));
      params.set('ordering', '-timestamp');
      if (sensorId) {
        params.set('sensor', sensorId);
      } else if (equipamentoId) {
        params.set('sensor__equipamento', equipamentoId);
      } else if (allowedEqIds && allowedEqIds.size) {
        params.set('sensor__equipamento__in', [...allowedEqIds].join(','));
      }
      if (timestampDe) params.set('timestamp_de', timestampDe);
      if (timestampAte) params.set('timestamp_ate', timestampAte);
      return '/api/telemetria/leituras/?' + params.toString();
    }

    const testerMode = ref(false);
    function toggleTesterMode() { testerMode.value = !testerMode.value; }

    function donutArcs(segments, r = 52, cx = 64, cy = 64) {
      const total = segments.reduce((s, g) => s + g.value, 0);
      if (!total) return [];
      let angle = -Math.PI / 2;
      return segments.map(seg => {
        const sweep = (seg.value / total) * 2 * Math.PI;
        const x1 = cx + r * Math.cos(angle);
        const y1 = cy + r * Math.sin(angle);
        const x2 = cx + r * Math.cos(angle + sweep);
        const y2 = cy + r * Math.sin(angle + sweep);
        const large = sweep > Math.PI ? 1 : 0;
        const d = `M${cx},${cy} L${x1.toFixed(2)},${y1.toFixed(2)} A${r},${r} 0 ${large},1 ${x2.toFixed(2)},${y2.toFixed(2)} Z`;
        angle += sweep;
        return { ...seg, d, pct: Math.round((seg.value / total) * 100) };
      });
    }

    const chartCustoEvolucao = computed(() => {
      const dailyCosts = {};
      let totalPecas = 0;
      let totalMaoDeObra = 0;
      let osCount = 0;
      let highestCost = 0;
      let highestCostDate = '';

      lists.historico.forEach(h => {
        if (dashCustoSetor.value) {
          const osId = typeof h.ordem_servico === 'object' ? h.ordem_servico?.id : h.ordem_servico;
          const os = lists.ordens.find(o => o.id === osId);
          if (os) {
            const loc = lists.localizacoes.find(l => l.equipamento === os.equipamento);
            if (!loc || loc.setor !== dashCustoSetor.value) return;
          } else {
            return;
          }
        }
        const date = h.data_execucao;
        if (!date) return;

        const pecas = parseFloat(h.custo_pecas) || 0;
        const mao = parseFloat(h.custo_mao_de_obra) || 0;
        const total = pecas + mao;

        totalPecas += pecas;
        totalMaoDeObra += mao;
        osCount += 1;

        dailyCosts[date] = (dailyCosts[date] || 0) + total;
      });

      const sortedDates = Object.keys(dailyCosts).sort();
      if (sortedDates.length < 2) {
        return { path: '', area: '', dots: [], min: 0, max: 0, total: 0, xLabels: [], yTicks: [], summary: null };
      }

      const vals = sortedDates.map(d => {
        if (dailyCosts[d] > highestCost) {
            highestCost = dailyCosts[d];
            highestCostDate = d;
        }
        return dailyCosts[d];
      });
      const max = Math.max(...vals, 1);
      const chartRange = max;
      
      const W = 320, H = 100;
      const padding = 16;
      const leftPad = 45;
      const chartW = W - leftPad;

      const points = sortedDates.map((date, i) => {
        const v = dailyCosts[date];
        return {
          x: leftPad + (i / (sortedDates.length - 1)) * chartW,
          y: padding + (1 - (v / chartRange)) * (H - padding * 2),
          v,
          label: date.split('-').reverse().join('/'),
        };
      });

      const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
      const area = path + ` L${W},${H} L${leftPad},${H} Z`;

      const yTicks = Array.from({ length: 4 }, (_, idx) => {
        const value = (max * idx) / 3;
        // Format to 1k if >= 1000 for better fit
        const label = value >= 1000 ? (value/1000).toFixed(1) + 'k' : value.toFixed(0);
        return { y: padding + (1 - (value / max)) * (H - padding * 2), label };
      });

      const xLabels = [
        { x: leftPad, label: points[0].label.substring(0, 5) },
        { x: leftPad + chartW / 2, label: points[Math.floor(points.length / 2)].label.substring(0, 5) },
        { x: W, label: points[points.length - 1].label.substring(0, 5) },
      ];

      const totalCost = vals.reduce((a, b) => a + b, 0);

      const summary = {
          totalPecas: totalPecas.toFixed(2),
          totalMaoDeObra: totalMaoDeObra.toFixed(2),
          osCount,
          avgCost: osCount ? (totalCost / osCount).toFixed(2) : '0.00',
          highestCost: highestCost.toFixed(2),
          highestCostDate: highestCostDate ? highestCostDate.split('-').reverse().join('/') : ''
      };

      return {
        path, area, dots: points,
        min: 0, max: max.toFixed(0),
        total: totalCost.toFixed(2),
        yTicks, xLabels, leftPad, summary
      };
    });

    const availableSectors = computed(() => {
      const sectors = lists.localizacoes.map(l => l.setor).filter(Boolean);
      return [...new Set(sectors)].sort();
    });

    // ─ Toast ─────────────────────────────────────────
    function toast(msg, type = 'success') {
      const id = Date.now() + Math.random();
      toasts.value.push({ id, msg, type });
      setTimeout(() => { toasts.value = toasts.value.filter(t => t.id !== id); }, 4500);
    }

    // ─ API ───────────────────────────────────────────
    let refreshingPromise = null;

    async function doRefreshToken() {
      if (!refreshTk.value) throw new Error('No refresh token');
      const res = await fetch(BASE + '/api/auth/refresh/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshTk.value })
      });
      if (!res.ok) throw new Error('Refresh failed');
      const data = await res.json();
      token.value = data.access;
      localStorage.setItem('sentinel_token', data.access);
      if (data.refresh) {
        refreshTk.value = data.refresh;
        localStorage.setItem('sentinel_refresh', data.refresh);
      }
    }

    async function api(path, opts = {}) {
      const headers = { 'Content-Type': 'application/json' };
      if (token.value) headers['Authorization'] = `Bearer ${token.value}`;
      let res = await fetch(BASE + path, { headers, ...opts });

      if (res.status === 401 && refreshTk.value) {
        if (!refreshingPromise) {
          refreshingPromise = doRefreshToken().finally(() => { refreshingPromise = null; });
        }
        try {
          await refreshingPromise;
          headers['Authorization'] = `Bearer ${token.value}`;
          res = await fetch(BASE + path, { headers, ...opts });
        } catch {
          logout();
          return null;
        }
      }

      if (res.status === 401) { logout(); return null; }
      if (res.status === 204) return null;

      const contentType = (res.headers.get('content-type') || '').toLowerCase();
      if (contentType.includes('application/json')) {
        const body = await res.json();
        if (!res.ok) {
          const err = new Error(`API error ${res.status}`);
          err.fieldErrors = body;
          err.status = res.status;
          throw err;
        }
        return body;
      }

      const text = await res.text();
      if (!res.ok) {
        const err = new Error(`API error ${res.status}`);
        err.status = res.status;
        err.rawText = text;
        throw err;
      }
      try {
        return JSON.parse(text);
      } catch {
        return text;
      }
    }

    function parseDjangoErrors(raw) {
      const out = {};
      if (!raw || typeof raw !== 'object') return out;
      for (const [key, val] of Object.entries(raw)) {
        const msg = Array.isArray(val) ? val[0] : String(val);
        if (key === 'non_field_errors' || key === 'detail') out._global = msg;
        else out[key] = msg;
      }
      return out;
    }

    const timers = {};
    function debouncedFetch(key, fn, ms = 350) {
      clearTimeout(timers[key]);
      timers[key] = setTimeout(fn, ms);
    }

    // ─ Auth ──────────────────────────────────────────
    async function doLogin() {
      loginLoading.value = true; loginError.value = '';
      try {
        const res = await fetch(BASE + '/api/auth/login/', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(loginForm)
        });
        const data = await res.json();
        if (!data.access) throw new Error(data.detail || 'Credenciais inválidas');
        token.value = data.access;
        localStorage.setItem('sentinel_token', data.access);
        if (data.refresh) {
          refreshTk.value = data.refresh;
          localStorage.setItem('sentinel_refresh', data.refresh);
        }
        await fetchMe();
        await fetchEmpresasAll();
        resetTrendMonitoring();
        navigate('dashboard');
        startTrendPolling();
      } catch (e) { loginError.value = e.message; }
      finally { loginLoading.value = false; }
    }

    async function fetchMe() {
      try { me.value = await api('/api/auth/me/'); } catch { }
    }

    function logout() {
      clearOsPrompt();
      closeABC(); closeEquipModal();
      ++dashboardRequest; dashboardKpisLoading.value = false; dashboardSummary.value = null; dashboardUpdatedAt.value = null; liveOpen.value = false; telemetryLiveOpen.value = false; performanceOpen.value = false;
      stopTrendPolling(); resetTrendMonitoring(); clearTrendDemo();
      ++dashboardSummaryRequest; dashboardSummary.value = null; dashAlerts.value = []; alertCount.value = 0;
      ++alertRequest; closeAlertaDetails(); lists.alertas = []; alertHistory.count = 0; alertHistory.url = ''; alertCount.value = 0;
      ++telemetryRequest; ++telemetryOptionsRequest; ++trendPageRequest;
      Object.assign(telemetry, { rows: [], equipments: [], sensors: [], count: 0, busy: false, updatedAt: null });
      Object.assign(trendPage, { equipment: '', sensor: '', search: '', equipmentSearch: '', chartMode: 'live', listOpen: false, condition: '', rows: [], detail: null, offset: 0, busy: false, updatedAt: null, error: '' });
      token.value = ''; refreshTk.value = ''; me.value = null;
      globalEmpresa.value = ''; dashSetor.value = ''; dashEquipamento.value = ''; dashboardTab.value = 'minhas';
      for (const resource of Object.keys(lists)) lists[resource] = [];
      localStorage.removeItem('sentinel_token');
      localStorage.removeItem('sentinel_refresh');
    }

    // ─ Navigation ────────────────────────────────────
    const fetchers = {
      dashboard: () => fetchDashboard(),
      equipamentos: () => fetchEquipamentos(),
      alertas: () => enterAlertHistory(),
      ordens: () => fetchOrdens(),
      telemetria: () => enterTelemetry(),
      tendencias: () => fetchTrends(),
      historico: () => fetchHistorico(),
      empresas: () => fetchEmpresas(),
      usuarios: () => fetchUsuarios(),
      localizacoes: () => fetchLocalizacoes(),
      prompts: () => fetchPrompts(),
    };
    function navigate(v) {
      if (v === 'prompts' && !isAdminOrGestor.value) return;
      view.value = v; fetchers[v]?.();
    }

    // Navegação dos cards clicáveis do técnico no dashboard
    function navigateMinhasOrdens() { return openDashboardOrders(); }
    function navigateOsSemTecnico() { return openDashboardOrders('livres'); }

    // ─ Fetchers ──────────────────────────────────────
    async function withLoading(fn) {
      loading.value = true;
      try { await fn(); }
      finally { loading.value = false; }
    }

    function normList(d) {
      return Array.isArray(d) ? d : (d?.results ?? []);
    }
    function normPages(d) {
      return { next: d?.next ?? null, prev: d?.previous ?? null };
    }

    async function fetchDashboard({ silent = false } = {}) {
      if (silent && dashboardKpisLoading.value) return;
      const request = ++dashboardRequest, company = globalEmpresa.value, userId = me.value?.id;
      dashboardKpisLoading.value = true; dashboardKpisError.value = '';
      const p = new URLSearchParams({ incluir_desempenho: String(performanceOpen.value && !dashboardAdminOverview.value && !isTecnico.value) });
      if (company) p.set('empresa_id', company);
      if (dashSetor.value) p.set('setor', dashSetor.value);
      if (dashEquipamento.value) p.set('equipamento_id', dashEquipamento.value);
      try {
        const data = await api('/api/dashboards/resumo/?' + p);
        if (request !== dashboardRequest || company !== globalEmpresa.value || userId !== me.value?.id || view.value !== 'dashboard' || !data) return;
        dashboardSummary.value = data; dashboardUpdatedAt.value = data.atualizado_em;
        if (!isAdmin.value && data.empresa_atual) lists.empresas = [data.empresa_atual];
        dashboardKpis.value = data.detalhes_equipamentos || [];
        dashAlerts.value = data.alertas_recentes || []; alertCount.value = data.alertas_24h?.total || 0;
        kpis.value = { total_equipamentos: data.resumo_status?.total, alertas_ativos: data.alertas_ativos?.total, alertas_24h: data.alertas_24h?.total, ordens_abertas: data.os_abertas };
        if (isAdmin.value && data.empresas) lists.empresas = data.empresas.map(c => ({ id: c.id, nome: c.nome }));
      } catch (_) {
        if (request === dashboardRequest) dashboardKpisError.value = 'Não foi possível atualizar o dashboard. Os dados anteriores, quando disponíveis, foram preservados.';
      } finally { if (request === dashboardRequest) dashboardKpisLoading.value = false; }
    }

    function acceptTrendSnapshot(data) {
      const anomalies = data.filter(trend => trend.is_anomalous && trend.analysis_enabled && !trend.insufficient_data);
      const current = new Map(anomalies.map(trend => [`${trend.sensor_id}:${trend.direction}`, trend.active_alert_id]));
      if (knownTrendConditions !== null) {
        for (const [key, alertId] of current) {
          const previous = knownTrendConditions.get(key);
          if (!knownTrendConditions.has(key) || (previous != null && alertId != null && previous !== alertId))
            trendMonitor.newCount++;
        }
      }
      knownTrendConditions = current;
      trendAlerts.value = anomalies;
      trendMonitor.updatedAt = new Date().toISOString();
      trendMonitor.error = '';
    }
    async function refreshTrendMonitoring() {
      if (!token.value || document.hidden || trendMonitor.busy ||
          (view.value === 'tendencias' && trendPage.busy)) return;
      const request = ++trendMonitorRequest;
      const company = globalEmpresa.value, session = token.value;
      const showAll = view.value === 'tendencias';
      const pageVersion = trendPageRequest;
      trendMonitor.busy = true;
      try {
        const query = new URLSearchParams();
        if (showAll) query.set('all', 'true');
        if (company) query.set('empresa_id', company);
        const data = await api('/api/telemetria/tendencias/?' + query);
        if (request !== trendMonitorRequest || company !== globalEmpresa.value || !token.value || session !== token.value) return;
        if (!Array.isArray(data)) throw new Error('Resposta de tendências indisponível.');
        acceptTrendSnapshot(data);
        if (showAll && view.value === 'tendencias' &&
            pageVersion === trendPageRequest && !trendPage.busy) {
          trendPage.rows = data;
          ensureTrendSelection();
          const total = filteredTrends.value.length;
          if (trendPage.offset >= total) trendPage.offset = total ? Math.floor((total - 1) / trendPage.size) * trendPage.size : 0;
          if (trendPage.detail) trendPage.detail = data.find(t => t.sensor_id === trendPage.detail.sensor_id) || null;
          trendPage.updatedAt = trendMonitor.updatedAt;
          trendPage.error = '';
        }
      } catch {
        if (request === trendMonitorRequest) trendMonitor.error = 'Não foi possível atualizar as tendências. Exibindo a última consulta disponível; nova tentativa em até 30 segundos.';
      } finally {
        if (request === trendMonitorRequest) trendMonitor.busy = false;
      }
    }
    async function fetchTrendAlerts() {
      await refreshTrendMonitoring();
    }
    function reviewNewTrends() {
      trendMonitor.newCount = 0;
      showTrends();
      trendPage.condition = 'anomalous';
    }

    async function analyzeSensorTrendAI(sensorId) {
      if (!sensorId) return;
      trendAILoading[sensorId] = true;
      try {
        const data = await api('/api/gemini/tendencia/', {
          method: 'POST',
          body: JSON.stringify({ 
            sensor_id: sensorId,
            message: "Gere um diagnóstico preditivo para a tendência atual deste sensor." 
          })
        });
        if (data && data.response) {
          if (!trendDataCache[sensorId]) trendDataCache[sensorId] = {};
          trendDataCache[sensorId].ai_analysis = data.response;
        }
      } catch (err) {
        toast('Erro ao analisar tendência com IA', 'error');
      } finally {
        trendAILoading[sensorId] = false;
      }
    }

    async function fetchTrendForSensor(sensorId) {
      if (!sensorId) return null;
      try {
        const data = await api(`/api/telemetria/tendencias/?sensor_id=${sensorId}`);
        if (data && !data.detail) {
          if (!trendDataCache[sensorId]) trendDataCache[sensorId] = {};
          // Preserve ai_analysis se existir
          trendDataCache[sensorId] = { ...data, ai_analysis: trendDataCache[sensorId].ai_analysis };
          return data;
        }
      } catch (err) {
        console.error('Erro ao buscar tendência do sensor', err);
      }
      return null;
    }

    let trendConfigRequest = 0;
    let trendConfigTrigger = null;
    async function openTrendConfig(sensorId, equipamentoId) {
      const request = ++trendConfigRequest;
      if (!trendConfigModal.open) trendConfigTrigger = document.activeElement;
      trendConfigModal.sensorId = sensorId;
      trendConfigModal.equipamentoId = equipamentoId;
      trendConfigModal.loading = true;
      trendConfigModal.open = true;
      nextTick(() => document.getElementById('trend-config-close')?.focus());
      trendConfigModal.isGlobal = false;
      trendConfigModal.error = '';
      
      try {
        // Fetch specific config
        const data = await api(sensorId ? `/api/telemetria/trend-config/?sensor=${sensorId}` : '/api/telemetria/trend-config/?sensor__isnull=true');
        if (request !== trendConfigRequest) return;
        const results = normList(data);
        if (results && results.length > 0) {
          const config = results[0];
          trendConfigModal.form = { ...config };
          trendConfigModal.isGlobal = false;
        } else if (!sensorId) {
          trendConfigModal.form = { ativo:true, periodo_horas:24, num_leituras:50, minimo_leituras:3, duracao_minima_minutos:120, antecedencia_os_minutos:120, persistencia_minima:0.7, r2_minimo:0.8, direcao_alerta:'crescente', sensibilidade:'media' };
        } else {
          // Usa a configuração efetiva, incluindo a global visível pelo backend.
          const trend = await api(`/api/telemetria/tendencias/?sensor_id=${sensorId}`);
          if (request !== trendConfigRequest) return;
          trendConfigModal.form = { ...trend.config_used };
          trendConfigModal.isGlobal = true;
        }
      } catch (err) {
        if (request !== trendConfigRequest) return;
        closeTrendConfig(true);
        toast('Erro ao carregar configuração de tendência', 'error');
      } finally {
        if (request === trendConfigRequest) trendConfigModal.loading = false;
      }
    }

    async function saveTrendConfig() {
      trendConfigModal.saving = true;
      trendConfigModal.error = '';
      try {
        const payload = {
          sensor: trendConfigModal.sensorId,
          periodo_horas: trendConfigModal.form.periodo_horas,
          num_leituras: trendConfigModal.form.num_leituras,
          minimo_leituras: trendConfigModal.form.minimo_leituras,
          duracao_minima_minutos: trendConfigModal.form.duracao_minima_minutos,
          antecedencia_os_minutos: trendConfigModal.form.antecedencia_os_minutos,
          persistencia_minima: trendConfigModal.form.persistencia_minima,
          r2_minimo: trendConfigModal.form.r2_minimo,
          direcao_alerta: trendConfigModal.form.direcao_alerta,
          sensibilidade: trendConfigModal.form.sensibilidade,
          ativo: trendConfigModal.form.ativo
        };
        
        let url = '/api/telemetria/trend-config/';
        let method = 'POST';
        
        if (trendConfigModal.form.id) {
          url += `${trendConfigModal.form.id}/`;
          method = 'PUT';
        }
        
        await api(url, { method, body: JSON.stringify(payload) });
        toast('Configuração de tendência salva', 'success');
        closeTrendConfig(true);
        
        if (view.value === 'tendencias') await fetchTrends();
        // Refresh trend data if open
        if (equipModal.open) {
          fetchTrendForSensor(trendConfigModal.sensorId);
        }
      } catch (err) {
        trendConfigModal.error = err.fieldErrors ? Object.entries(err.fieldErrors).map(([field, messages]) => `${field}: ${[].concat(messages).join(' ')}`).join(' · ') : 'Não foi possível salvar. Confira os critérios e tente novamente.';
        toast('Erro ao salvar configuração', 'error');
      } finally {
        trendConfigModal.saving = false;
      }
    }

    function closeTrendConfig(force = false) {
      if (trendConfigModal.saving && !force) return;
      ++trendConfigRequest;
      trendConfigModal.open = false;
      const trigger = trendConfigTrigger;
      trendConfigTrigger = null;
      nextTick(() => { if (trigger?.isConnected) trigger.focus(); });
    }
    function trendConfigKeydown(event) {
      if (event.key === 'Escape') { event.stopPropagation(); closeTrendConfig(); }
      if (event.key !== 'Tab') return;
      const controls = [...event.currentTarget.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), summary, [href]')]
        .filter(element => element.getClientRects().length);
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }

    async function fetchEquipamentos() {
      await withLoading(async () => {
        const p = new URLSearchParams();
        if (filters.equipamentos.search) p.set('search', filters.equipamentos.search);
        if (filters.equipamentos.status) p.set('status', filters.equipamentos.status);
        if (filters.equipamentos.setor) p.set('localizacao__setor', filters.equipamentos.setor);
        const empFilter = filters.equipamentos.empresa || globalEmpresa.value;
        if (empFilter) p.set('empresa', empFilter);
        const d = await api('/api/equipamentos/?' + p);
        lists.equipamentos = normList(d);
        Object.assign(pages.equipamentos, normPages(d));
        // Busca localizações para mostrar o setor ao lado de cada equipamento
        const locRes = await api('/api/localizacao/?limit=999');
        lists.localizacoes = normList(locRes);
        // Busca todos os sensores para exibir a contagem na tabela de equipamentos
        await fetchSensoresAll();
      });
    }

    function alertParams() {
      const f = filters.alertas;
      const p = new URLSearchParams();
      for (const key of ['search', 'nivel', 'origem', 'equipamento', 'sensor', 'status', 'setor'])
        if (f[key] !== '') p.set(key, f[key]);
      if (f.from && f.to && new Date(f.from) > new Date(f.to))
        throw new Error('A data inicial deve ser anterior à data final.');
      if (f.from) p.set('data_de', new Date(f.from).toISOString());
      if (f.to) p.set('data_ate', new Date(f.to).toISOString());
      if (globalEmpresa.value) p.set('equipamento__empresa', globalEmpresa.value);
      return p;
    }
    async function enterAlertHistory() {
      return Promise.all([loadTelemetryOptions(), fetchAlertas()]);
    }
    async function fetchAlertas(url = null, { silent = false } = {}) {
      const request = ++alertRequest;
      if (!silent) alertHistory.busy = true;
      alertHistory.error = '';
      try {
        const path = typeof url === 'string' ? url.replace(/^https?:\/\/[^/]+/, '') : '/api/alertas/?' + alertParams();
        const data = await api(path);
        if (request !== alertRequest) return;
        if (!data) throw new Error('Não foi possível consultar o histórico. Entre novamente.');
        lists.alertas = normList(data);
        alertHistory.url = path;
        alertHistory.count = data.count ?? lists.alertas.length;
        Object.assign(pages.alertas, normPages(data));
      } catch (error) {
        if (request === alertRequest) alertHistory.error = error.message || 'Não foi possível carregar o histórico.';
      } finally {
        if (request === alertRequest) alertHistory.busy = false;
      }
    }
    async function openAlertaDetails(alerta) {
      const request = ++alertDetailRequest;
      alertHistory.detail = alerta;
      nextTick(() => document.getElementById('alert-detection-dialog')?.focus());
      alertHistory.detailBusy = true;
      alertHistory.detailError = '';
      closeEquipModal();
      try {
        const data = await api('/api/alertas/' + alerta.id + '/');
        if (request === alertDetailRequest && alertHistory.detail) {
          if (!data) throw new Error('Registro indisponível.');
          alertHistory.detail = data;
        }
      } catch {
        if (request === alertDetailRequest) alertHistory.detailError = 'Não foi possível atualizar este registro. Tente novamente.';
      } finally {
        if (request === alertDetailRequest) alertHistory.detailBusy = false;
      }
    }
    function closeAlertaDetails() {
      ++alertDetailRequest;
      alertHistory.detail = null; alertHistory.detailBusy = false; alertHistory.detailError = '';
    }
    async function openAlertaOS(alerta) {
      if (!alerta.ordem_servico_id) return;
      return openOrderDetails({ id: alerta.ordem_servico_id });
    }
    async function openAlertaSensor(alerta) {
      if (!alerta.sensor) return;
      closeAlertaDetails();
      Object.assign(telemetry, { tab: 'leituras', equipment: alerta.equipamento, sensor: alerta.sensor,
        from: '', to: '', min: '', max: '', search: '', offset: 0 });
      view.value = 'telemetria';
      return Promise.all([loadTelemetryOptions(), fetchTelemetria()]);
    }
    function showEquipmentAlerts(equipment) {
      closeEquipModal(); closeAlertaDetails();
      Object.assign(filters.alertas, { equipamento: equipment, sensor: '', nivel: '', origem: '', from: '', to: '', search: '', status: '', setor: '' });
      view.value = 'alertas'; return enterAlertHistory();
    }

    const orderState = reactive({ busy: false, error: '', count: 0, total: 0, triage: 0 });
    const orderDetail = reactive({ open: false, id: null, order: null, busy: false, error: '' });
    const orderAnalysis = reactive({ busy: false, error: '', text: '' });
    let orderAnalysisRequest = 0;
    function resetOrderAnalysis() {
      ++orderAnalysisRequest;
      Object.assign(orderAnalysis, { busy: false, error: '', text: '' });
    }
    async function analyzeOrder() {
      if (!orderDetail.open || !orderDetail.order || orderDetail.busy || orderAnalysis.busy) return;
      const request = ++orderAnalysisRequest;
      const detailRequest = orderDetailRequest;
      const id = orderDetail.id, company = globalEmpresa.value, actor = me.value?.id;
      const current = () => request === orderAnalysisRequest && detailRequest === orderDetailRequest
        && orderDetail.open && orderDetail.id === id && company === globalEmpresa.value && actor === me.value?.id;
      Object.assign(orderAnalysis, { busy: true, error: '', text: '' });
      try {
        const data = await api(`/api/ordens-servico/${id}/analise-ia/`, { method: 'POST' });
        if (!current()) return;
        if (typeof data?.response !== 'string' || !data.response.trim()) throw new Error('Resposta vazia');
        orderAnalysis.text = data.response.trim();
      } catch (error) {
        if (current()) orderAnalysis.error = error.fieldErrors?.detail || 'Não foi possível gerar a análise. Tente novamente.';
      } finally { if (current()) orderAnalysis.busy = false; }
    }
    const orderExtraFilters = computed(() => [filters.ordens.tipo_os, filters.ordens.responsavel_escopo].filter(Boolean).length);
    let orderDetailRequest = 0;
    let orderDetailTrigger = null;
    const orderStatusLabel = status => ({ pendente: 'Pendente', andamento: 'Em andamento', concluida: 'Concluída', cancelada: 'Cancelada' }[status] || '—');
    const orderTypeLabel = type => ({ preventiva: 'Preventiva', corretiva: 'Corretiva', preditiva: 'Preditiva' }[type] || '—');
    const alertLevelLabel = level => ({ baixo: 'Baixo', medio: 'Médio', critico: 'Crítico' }[level] || 'Não registrado');
    function orderEscalations(order) {
      return (order.historico_alertas || []).flatMap(alert => (alert.historico_niveis || []).map(event => ({ ...event, alerta_id: alert.id })))
        .sort((a, b) => new Date(b.registrado_em || b.ocorrido_em) - new Date(a.registrado_em || a.ocorrido_em));
    }
    function orderLastEscalation(order) {
      return orderEscalations(order)[0] || null;
    }
    function fmtTimestamp(value) {
      if (!value) return '—';
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return '—';
      return date.toLocaleString('pt-BR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
    function focusOrderDetails() {
      nextTick(() => document.getElementById('order-detail-close')?.focus());
    }
    async function openOrderDetails(order) {
      resetOrderAnalysis();
      const request = ++orderDetailRequest;
      const company = globalEmpresa.value;
      const actor = me.value?.id;
      if (!orderDetail.open) orderDetailTrigger = document.activeElement;
      if (equipModal.open) closeEquipModal();
      if (alertHistory.detail) closeAlertaDetails();
      Object.assign(orderDetail, { open: true, id: order.id, order: null, busy: true, error: '' });
      focusOrderDetails();
      try {
        const current = await api('/api/ordens-servico/' + order.id + '/');
        if (request !== orderDetailRequest || company !== globalEmpresa.value || actor !== me.value?.id) return;
        if (!current?.id) throw new Error('Ordem indisponível');
        orderDetail.order = current;
      } catch {
        if (request === orderDetailRequest) orderDetail.error = 'Não foi possível carregar esta O.S. Tente novamente.';
      } finally { if (request === orderDetailRequest) orderDetail.busy = false; }
    }
    function closeOrderDetails() {
      resetOrderAnalysis();
      ++orderDetailRequest;
      Object.assign(orderDetail, { open: false, id: null, order: null, busy: false, error: '' });
      const trigger = orderDetailTrigger;
      orderDetailTrigger = null;
      nextTick(() => { if (trigger?.isConnected) trigger.focus(); });
    }
    function orderDetailKeydown(event) {
      if (event.key === 'Escape') { event.stopPropagation(); closeOrderDetails(); }
      if (event.key !== 'Tab') return;
      const controls = [...event.currentTarget.querySelectorAll('button:not(:disabled), summary, [href], [tabindex="0"]')]
        .filter(element => element.getClientRects().length);
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    function syncOrderDetails(saved) {
      if (!saved?.id) return;
      if (orderDetail.order?.id === saved.id) {
        resetOrderAnalysis();
        orderDetail.order = { ...orderDetail.order, ...saved, _assumindo: false };
      }
      const listed = lists.ordens.find(order => order.id === saved.id);
      if (listed) Object.assign(listed, saved);
    }
    let orderRequest = 0;
    function orderParams() {
      const p = new URLSearchParams();
      for (const key of ['responsavel_escopo', 'equipamento', 'setor', 'search', 'prioridade', 'tipo_os']) {
        if (filters.ordens[key]) p.set(key, String(filters.ordens[key]));
      }
      if (filters.ordens.status === 'abertas') p.set('abertas', 'true');
      else if (filters.ordens.status) p.set('status', filters.ordens.status);
      if (globalEmpresa.value) p.set('equipamento__empresa', globalEmpresa.value);
      return p;
    }
    async function fetchOrdens(url = null) {
      const request = ++orderRequest;
      orderState.busy = true; orderState.error = '';
      try {
        const path = typeof url === 'string' ? url.replace(/^https?:\/\/[^/]+/, '') : '/api/ordens-servico/?' + orderParams();
        const data = await api(path);
        if (request !== orderRequest) return;
        lists.ordens = normList(data);
        Object.assign(pages.ordens, normPages(data));
        orderState.count = data?.count ?? lists.ordens.length;
        orderState.total = data?.total_escopo ?? orderState.count;
        orderState.triage = data?.a_definir ?? 0;
      } catch (error) {
        if (request === orderRequest) { lists.ordens = []; orderState.count = 0; orderState.triage = 0; orderState.error = 'Não foi possível carregar as OS. Tente novamente.'; }
      } finally { if (request === orderRequest) orderState.busy = false; }
    }
    function selectOrderPriority(value) { filters.ordens.prioridade = value; return fetchOrdens(); }
    function clearOrderFilters() {
      Object.assign(filters.ordens, { search: '', status: 'abertas', prioridade: '', tipo_os: '', abertas: true,
        responsavel_escopo: '', equipamento: '', setor: '' });
      return fetchOrdens();
    }

    const equipmentGuide = reactive({ busy: false, error: '', current: null, types: [] });
    const criteriaModal = reactive({ open: false, busy: false, saving: false, error: '', company: '', data: {} });
    const equipmentAssessment = reactive({ busy: false, error: '', history: [] });
    const priorityModal = reactive({ open: false, busy: false, saving: false, error: '', order: null, history: [], choice: 'A', reason: '' });
    const orderEquipmentOptions = ref([]);
    let guideRequest = 0, criteriaRequest = 0, assessmentRequest = 0, priorityRequest = 0;
    function criticidadeLabel(value, legacy = false) { if (legacy && value) return value + ' — ' + ({A:'Crítica', B:'Alta', C:'Moderada', D:'Baixa'}[value] || value) + ' (legado)'; return { A: 'A — Alta criticidade', B: 'B — Média criticidade', C: 'C — Baixa criticidade', D: 'D — Baixa (legado)' }[value] || 'Não avaliada'; }
    function historicPriorityLabel(value) { return { alta: 'Alta (legado)', critica: 'Crítica (legado)', media: 'Média (legado)', baixa: 'Baixa (legado)' }[value] || prioridadeLabel(value); }
    function priorityOrigin(value) { return { herdada: 'Definição na abertura', ajustada: 'Ajuste de prioridade', ajuste: 'Ajuste de prioridade', restauracao: 'Prioridade da abertura restaurada', convertida: 'Conversão de registro antigo', migracao: 'Conversão de registro antigo' }[value] || 'Registro antigo'; }
    async function loadEquipmentGuide() {
      const request = ++guideRequest;
      equipmentGuide.current = null; equipmentGuide.types = []; equipmentGuide.error = '';
      const company = fd.empresa;
      if (!company) { equipmentGuide.busy = false; return; }
      equipmentGuide.busy = true;
      try {
        const [guide, types] = await Promise.all([
          api('/api/criterios-criticidade/atual/?empresa=' + company),
          telemetryAll('/api/tipos-equipamento/?empresa=' + company + '&limit=100'),
        ]);
        if (request === guideRequest) { equipmentGuide.current = guide; equipmentGuide.types = types; }
      } catch (error) { if (request === guideRequest) equipmentGuide.error = 'Não foi possível carregar os critérios da empresa.'; }
      finally { if (request === guideRequest) equipmentGuide.busy = false; }
    }
    function acceptEquipmentSuggestion() {
      const type = equipmentGuide.types.find(row => Number(row.id) === Number(fd.tipo_equipamento));
      if (type?.criticidade_padrao) { fd.criticidade = type.criticidade_padrao; fd.aceitar_sugestao = true; }
    }
    async function openCriteria(company = null) {
      criteriaModal.open = true; criteriaModal.error = ''; criteriaModal.data = {};
      criteriaModal.company = company || globalEmpresa.value || me.value?.empresa || '';
      await fetchEmpresasAll();
      return loadCriteria();
    }
    async function loadCriteria() {
      const request = ++criteriaRequest;
      criteriaModal.data = {}; criteriaModal.error = '';
      if (!criteriaModal.company) { criteriaModal.busy = false; return; }
      criteriaModal.busy = true;
      try {
        const data = await api('/api/criterios-criticidade/atual/?empresa=' + criteriaModal.company);
        if (request === criteriaRequest) criteriaModal.data = data || {};
      } catch (error) { if (request === criteriaRequest) criteriaModal.error = 'Não foi possível carregar os critérios.'; }
      finally { if (request === criteriaRequest) criteriaModal.busy = false; }
    }
    async function saveCriteria() {
      const request = criteriaRequest;
      const actor = me.value?.id;
      criteriaModal.saving = true; criteriaModal.error = '';
      try {
        const payload = { empresa: Number(criteriaModal.company) };
        for (const key of ['criterio_a', 'criterio_b', 'criterio_c', 'representante_manutencao', 'data_validacao']) payload[key] = criteriaModal.data[key];
        const saved = await api('/api/criterios-criticidade/', { method: 'POST', body: JSON.stringify(payload) });
        if (!saved || request !== criteriaRequest || actor !== me.value?.id || !criteriaModal.open) return;
        criteriaModal.open = false;
        if (modal.open && modal.type === 'equipamento' && Number(fd.empresa) === Number(saved.empresa)) await loadEquipmentGuide();
        toast('Nova revisão dos critérios registrada.', 'success');
      } catch (error) { criteriaModal.error = Object.values(parseDjangoErrors(error.fieldErrors || { detail: error.message })).join(' '); }
      finally { criteriaModal.saving = false; }
    }
    async function loadEquipmentAssessment(equipment) {
      const request = ++assessmentRequest;
      equipmentAssessment.busy = true; equipmentAssessment.error = ''; equipmentAssessment.history = [];
      try {
        const rows = await telemetryAll('/api/historico-criticidade/?equipamento=' + equipment.id + '&limit=100');
        if (request === assessmentRequest) equipmentAssessment.history = rows;
      } catch (error) { if (request === assessmentRequest) equipmentAssessment.error = 'Não foi possível carregar o histórico de criticidade.'; }
      finally { if (request === assessmentRequest) equipmentAssessment.busy = false; }
    }
    async function openPriority(order) {
      const request = ++priorityRequest;
      Object.assign(priorityModal, { open: true, busy: true, error: '', order: null, history: [], reason: '' });
      try {
        const [current, history] = await Promise.all([
          api('/api/ordens-servico/' + order.id + '/'),
          telemetryAll('/api/ordens-servico/' + order.id + '/historico_prioridade/?limit=100'),
        ]);
        if (request === priorityRequest) Object.assign(priorityModal, { order: current, history, choice: current?.prioridade || 'A' });
      } catch (error) { if (request === priorityRequest) priorityModal.error = 'Não foi possível carregar a prioridade e seu histórico.'; }
      finally { if (request === priorityRequest) priorityModal.busy = false; }
    }
    async function savePriority(restore = false) {
      if (!priorityModal.reason.trim()) { priorityModal.error = 'Informe a justificativa da alteração.'; return; }
      const request = priorityRequest;
      const actor = me.value?.id;
      priorityModal.saving = true; priorityModal.error = '';
      try {
        const payload = { justificativa: priorityModal.reason.trim() };
        if (!restore) payload.prioridade = priorityModal.choice;
        const saved = await api('/api/ordens-servico/' + priorityModal.order.id + '/' + (restore ? 'restaurar_prioridade' : 'ajustar_prioridade') + '/', { method: 'POST', body: JSON.stringify(payload) });
        if (!saved || request !== priorityRequest || actor !== me.value?.id || !priorityModal.open) return;
        syncOrderDetails(saved);
        if (equipModal.open) await fetchEquipamentoOrdens(equipModal.equipamento.id);
        await openPriority(saved);
        if (view.value === 'ordens') await fetchOrdens();
        else if (view.value === 'dashboard') await fetchDashboard();
        toast('Prioridade registrada com justificativa.', 'success');
      } catch (error) { priorityModal.error = Object.values(parseDjangoErrors(error.fieldErrors || { detail: error.message })).join(' '); }
      finally { priorityModal.saving = false; }
    }
    function closeABC() {
      closeOrderDetails();
      ++guideRequest; ++criteriaRequest; ++assessmentRequest; ++priorityRequest; ++orderRequest;
      criteriaModal.open = false; priorityModal.open = false; modal.open = false;
      equipmentGuide.current = null; equipmentGuide.types = []; equipmentGuide.busy = false;
      equipmentAssessment.history = []; equipmentAssessment.busy = false;
      priorityModal.order = null; priorityModal.history = []; criteriaModal.data = {};
      orderEquipmentOptions.value = []; lists.ordens = []; orderState.error = ''; orderState.count = 0; orderState.total = 0; orderState.triage = 0; orderState.busy = false;
    }

    const telemetry = reactive({
      tab: 'leituras', busy: false, error: '', updatedAt: null,
      equipment: '', sensor: '', search: '', tipo: '', ativo: '',
      min: '', max: '', from: '', to: '', size: 20, offset: 0,
      rows: [], count: 0, equipments: [], sensors: [], optionsError: '',
    });
    const trendPage = reactive({
      equipment: '', sensor: '', condition: '', size: 20, offset: 0,
      search: '', equipmentSearch: '', chartMode: 'live', listOpen: false,
      rows: [], busy: false, error: '', updatedAt: null, detail: null,
    });
    let trendPageRequest = 0;
    const trendEquipments = computed(() => [...new Map(trendPage.rows.map(trend =>
      [trend.sensor_info.equipamento_id, { id: trend.sensor_info.equipamento_id, nome: trend.sensor_info.equipamento_nome }])).values()]
      .sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')));
    const trendEquipmentOptions = computed(() => trendEquipments.value.filter(e =>
      searchKey(e.nome).includes(searchKey(trendPage.equipmentSearch))));
    function searchKey(value) { return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('pt-BR').trim(); }
    const trendSensors = computed(() => trendPage.rows.filter(trend => !trendPage.equipment ||
      Number(trend.sensor_info.equipamento_id) === Number(trendPage.equipment))
      .map(trend => trend.sensor_info).sort((a, b) => a.nome.localeCompare(b.nome, 'pt-BR')));
    let telemetryRequest = 0;
    let telemetryOptionsRequest = 0;
    const telemetrySensors = computed(() => telemetry.sensors.filter(sensor =>
      !telemetry.equipment || Number(sensor.equipamento) === Number(telemetry.equipment)));
    function trendCondition(trend) {
      if (!trend.analysis_enabled) return 'disabled';
      if (trend.insufficient_data) return 'insufficient';
      return trend.is_anomalous ? 'anomalous' : 'normal';
    }
    function trendConditionLabel(trend) {
      return { disabled: 'Análise desativada', insufficient: 'Aguardando dados',
        anomalous: 'Anomalia confirmada', normal: 'Sem tendência anormal' }[trendCondition(trend)];
    }
    function trendDirection(trend) {
      if (['disabled', 'insufficient'].includes(trendCondition(trend))) return '—';
      return { increasing: 'Crescente', decreasing: 'Decrescente', stable: 'Estável' }[trend.direction] || '—';
    }
    const scopedTrends = computed(() => trendPage.rows.filter(trend =>
      (!trendPage.equipment || Number(trend.sensor_info.equipamento_id) === Number(trendPage.equipment)) &&
      searchKey(trend.sensor_info.nome + ' ' + trend.sensor_info.equipamento_nome + ' ' + trend.sensor_info.tipo_display).includes(searchKey(trendPage.search))));
    const filteredTrends = computed(() => scopedTrends.value.filter(trend =>
      !trendPage.condition || trendCondition(trend) === trendPage.condition));
    const scopedTrendCount = computed(() => scopedTrends.value.length);
    const telemetryCount = computed(() => telemetry.count);
    const telemetryRows = computed(() => telemetry.rows);
    const trendCount = computed(() => filteredTrends.value.length);
    const trendRows = computed(() => filteredTrends.value.slice(trendPage.offset, trendPage.offset + trendPage.size));
    const trendSummary = computed(() => ({
      anomalous: scopedTrends.value.filter(t => trendCondition(t) === 'anomalous').length,
      normal: scopedTrends.value.filter(t => trendCondition(t) === 'normal').length,
      insufficient: scopedTrends.value.filter(t => trendCondition(t) === 'insufficient').length,
      disabled: scopedTrends.value.filter(t => trendCondition(t) === 'disabled').length,
    }));
    const selectedTrend = computed(() => trendPage.rows.find(trend => trend.sensor_id === Number(trendPage.sensor)) || null);
    function trendMinutes(value) {
      const minutes = Number(value);
      if (!Number.isFinite(minutes)) return '—';
      return minutes >= 60 ? Math.floor(minutes / 60) + ' h' + (minutes % 60 ? ' ' + Math.round(minutes % 60) + ' min' : '') : Math.round(minutes) + ' min';
    }
    function trendInterventionLabel(trend) {
      return {disabled:'Análise desativada', insufficient_data:'Aguardando histórico e leituras suficientes',
        no_anomaly:'Sem tendência anormal confirmada', no_upper_limit_projection:'Sem projeção para o limite superior',
        expired_projection:'Estimativa vencida · aguardando novas leituras', limit_reached:'Limite atingido · consultar alerta por limite',
        outside_horizon:'Previsão além da antecedência · em acompanhamento', within_horizon:'Previsão dentro da antecedência da O.S.'}[trend?.intervention_reason] || 'Aguardando análise';
    }
    const trendPersistencePercent = computed({get:() => Math.round(trendConfigModal.form.persistencia_minima * 100), set:value => { trendConfigModal.form.persistencia_minima = Number(value) / 100; }});
    const trendR2Percent = computed({get:() => Math.round(trendConfigModal.form.r2_minimo * 100), set:value => { trendConfigModal.form.r2_minimo = Number(value) / 100; }});
    function buildTrendChart(trend) {
      const rows = trend?.readings_summary || [];
      if (!rows.length) return { points: '', min: 0, max: 0, from: '', to: '', ticks: [], limitY: null, limit: null };
      const limit = Number(trend.sensor_info.limite_alerta);
      const values = rows.map(row => row.valor);
      const min = Math.min(...values, ...(Number.isFinite(limit) ? [limit] : []));
      const max = Math.max(...values, ...(Number.isFinite(limit) ? [limit] : []));
      const range = max - min || 1;
      const y = value => 150 - (value - min) / range * 115;
      const first = Date.parse(rows[0].timestamp), last = Date.parse(rows[rows.length - 1].timestamp);
      return { min, max, from: rows[0].timestamp, to: rows[rows.length - 1].timestamp,
        limit: Number.isFinite(limit) ? limit : null, limitY: Number.isFinite(limit) ? y(limit) : null,
        ticks: [min, min + range / 2, max].map(value => ({ value: Number(value.toFixed(2)), y: y(value) })),
        points: rows.map(row => `${55 + (Date.parse(row.timestamp) - first) / (last - first || 1) * 600},${y(row.valor)}`).join(' ') };
    }
    const trendChart = computed(() => buildTrendChart(trendPage.detail));
    const selectedTrendChart = computed(() => buildTrendChart(selectedTrend.value));
    function setTrendTimePreset(minutes) {
      const form = trendConfigModal.form;
      form.duracao_minima_minutos = minutes;
      form.periodo_horas = Math.max(form.periodo_horas, Math.ceil(minutes / 60));
      if (minutes === 1) { form.minimo_leituras = 7; form.num_leituras = 500; }
    }
    const trendDemo = reactive({ busy: false, error: '', session: null, company: '', scenario: 'aumento' });
    let demoTimer = null;
    let demoRequest = 0;
    function stopDemoPolling() {
      if (demoTimer !== null) clearInterval(demoTimer);
      demoTimer = null;
    }
    function clearTrendDemo() {
      stopDemoPolling(); ++demoRequest;
      Object.assign(trendDemo, { session: null, busy: false, error: '', company: '' });
    }
    function acceptDemoSnapshot(data) {
      trendDemo.session = data;
      const analysis = data.analysis;
      if (analysis) {
        const index = trendPage.rows.findIndex(row => row.sensor_id === data.sensor_id);
        if (index === -1) trendPage.rows.push(analysis); else trendPage.rows[index] = analysis;
        if (trendPage.detail?.sensor_id === data.sensor_id) trendPage.detail = analysis;
        const others = trendAlerts.value.filter(row => row.sensor_id !== data.sensor_id);
        acceptTrendSnapshot([...others, analysis]);
        trendPage.updatedAt = analysis.analyzed_at;
      }
      if (data.status !== 'executando') stopDemoPolling();
    }
    function startDemoPolling() {
      stopDemoPolling();
      if (trendDemo.session?.status === 'executando') demoTimer = setInterval(() => {
        if (view.value === 'tendencias' && !document.hidden && testerMode.value && isAdmin.value && token.value)
          runTrendDemo('avancar');
      }, 2000);
    }
    async function runTrendDemo(action = 'criar', scenario = trendDemo.scenario) {
      if (!isAdmin.value || !testerMode.value || trendDemo.busy || !token.value) return;
      const company = globalEmpresa.value || trendDemo.company;
      if (action === 'criar' && !company) { trendDemo.error = 'Escolha a empresa que receberá o equipamento de demonstração.'; return; }
      if (action !== 'criar' && action !== 'retomar' && !trendDemo.session) return;
      const request = ++demoRequest, context = globalEmpresa.value, ownerId = me.value?.id;
      trendDemo.busy = true; trendDemo.error = '';
      try {
        const path = '/api/telemetria/tendencias/demo/' + (['criar', 'retomar'].includes(action) ? '' : trendDemo.session.id + '/');
        const data = action === 'retomar' ? await api(path) : await api(path, { method: 'POST', body: JSON.stringify(
          action === 'criar' ? { empresa: Number(company), cenario: scenario } : { acao: action, cenario: scenario }) });
        if (request !== demoRequest || context !== globalEmpresa.value || !token.value || ownerId !== me.value?.id) return;
        if (!data) throw new Error('Nenhuma demonstração encontrada. Inicie um teste.');
        if (context && Number(data.empresa_id) !== Number(context)) throw new Error('O último teste pertence a outra empresa. Selecione a empresa correspondente ou inicie um novo.');
        acceptDemoSnapshot(data);
        if (['criar', 'fase', 'retomar'].includes(action)) {
          Object.assign(trendPage, { equipment: data.equipamento_id, sensor: data.sensor_id, condition: '', offset: 0, detail: null });
          startDemoPolling();
          nextTick(() => document.getElementById('trend-live-monitor')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
        }
      } catch (error) {
        if (request === demoRequest) {
          trendDemo.error = error.fieldErrors ? Object.values(error.fieldErrors).flat().join(' ') : error.message;
          stopDemoPolling();
        }
      } finally {
        if (request === demoRequest) trendDemo.busy = false;
      }
    }
    async function toggleTrendTestMode() {
      toggleTesterMode();
      if (testerMode.value && !lists.empresas.length) {
        try { await fetchEmpresasAll(); } catch { trendDemo.error = 'Não foi possível carregar as empresas. Tente novamente.'; }
      }
      if (!testerMode.value) stopDemoPolling();
    }

    async function telemetryAll(path) {
      const result = [];
      while (path) {
        const data = await api(path.replace(/^https?:\/\/[^/]+/, ''));
        if (!data) throw new Error('Sessão indisponível. Entre novamente.');
        result.push(...normList(data));
        path = data.next;
      }
      return result;
    }
    async function loadTelemetryOptions() {
      const request = ++telemetryOptionsRequest;
      const company = globalEmpresa.value;
      telemetry.optionsError = '';
      try {
        const [equipments, sensors] = await Promise.all([
          telemetryAll('/api/equipamentos/?limit=100' + (company ? '&empresa=' + company : '')),
          telemetryAll('/api/telemetria/sensores/?limit=100' + (company ? '&equipamento__empresa=' + company : '')),
        ]);
        if (request !== telemetryOptionsRequest || company !== globalEmpresa.value) return;
        telemetry.equipments = equipments;
        telemetry.sensors = sensors;
      } catch {
        if (request === telemetryOptionsRequest) telemetry.optionsError = 'Não foi possível carregar os filtros de equipamentos e sensores.';
      }
    }
    async function fetchTelemetria() {
      const request = ++telemetryRequest;
      telemetry.busy = true;
      telemetry.error = '';
      const tab = telemetry.tab;
      try {
        if (tab === 'leituras') {
          if (telemetry.min !== '' && telemetry.max !== '' && Number(telemetry.min) > Number(telemetry.max))
            throw new Error('O valor mínimo deve ser menor ou igual ao máximo.');
          if (telemetry.from && telemetry.to && telemetry.from > telemetry.to)
            throw new Error('O início do período deve ser anterior ao fim.');
        }
        const query = new URLSearchParams({ limit: telemetry.size, offset: telemetry.offset });
        let endpoint;
        if (tab === 'sensores') {
          endpoint = '/api/telemetria/sensores/';
          if (globalEmpresa.value) query.set('equipamento__empresa', globalEmpresa.value);
          if (telemetry.equipment) query.set('equipamento', telemetry.equipment);
          if (telemetry.search.trim()) query.set('search', telemetry.search.trim());
          if (telemetry.tipo) query.set('tipo', telemetry.tipo);
          if (telemetry.ativo !== '') query.set('ativo', telemetry.ativo);
        } else {
          endpoint = '/api/telemetria/leituras/';
          if (globalEmpresa.value) query.set('sensor__equipamento__empresa', globalEmpresa.value);
          if (telemetry.equipment) query.set('sensor__equipamento', telemetry.equipment);
          if (telemetry.sensor) query.set('sensor', telemetry.sensor);
          if (telemetry.min !== '') query.set('valor_min', telemetry.min);
          if (telemetry.max !== '') query.set('valor_max', telemetry.max);
          if (telemetry.from) query.set('timestamp_de', new Date(telemetry.from).toISOString());
          if (telemetry.to) query.set('timestamp_ate', new Date(telemetry.to).toISOString());
        }
        const data = await api(endpoint + '?' + query);
        if (!data) throw new Error('Não foi possível carregar a telemetria. Entre novamente.');
        if (request !== telemetryRequest) return;
        telemetry.rows = normList(data);
        telemetry.count = data.count ?? telemetry.rows.length;
        if (telemetry.count > 0 && telemetry.offset >= telemetry.count) {
          telemetry.offset = Math.floor((telemetry.count - 1) / telemetry.size) * telemetry.size;
          await fetchTelemetria(); return;
        }
        telemetry.updatedAt = new Date().toISOString();
      } catch (err) {
        if (request === telemetryRequest) {
          telemetry.error = err.fieldErrors ? Object.values(err.fieldErrors).flat().join(' ') : err.message || 'Erro ao carregar telemetria.';
          telemetry.rows = []; telemetry.count = 0;
        }
      } finally {
        if (request === telemetryRequest) telemetry.busy = false;
      }
    }
    async function enterTelemetry() {
      await Promise.all([loadTelemetryOptions(), fetchTelemetria()]);
    }
    function setTelemetryTab(tab) {
      if (!['leituras', 'sensores'].includes(tab) || telemetry.tab === tab) return;
      telemetry.tab = tab; telemetry.offset = 0; telemetry.rows = []; telemetry.count = 0;
      fetchTelemetria();
    }
    function applyTelemetryFilters(equipmentChanged = false) {
      telemetry.offset = 0;
      if (equipmentChanged) telemetry.sensor = '';
      return fetchTelemetria();
    }
    function clearTelemetryFilters() {
      Object.assign(telemetry, { equipment: '', sensor: '', search: '', tipo: '', ativo: '',
        min: '', max: '', from: '', to: '', offset: 0 });
      fetchTelemetria();
    }
    function changeTelemetryPage(delta) {
      telemetry.offset = Math.max(0, telemetry.offset + delta * telemetry.size);
      return fetchTelemetria();
    }
    function sensorTipoLabel(tipo) { return {temperatura:'Temperatura', vibracao:'Vibração', pressao:'Pressão', corrente:'Corrente elétrica', umidade:'Umidade'}[tipo] || tipo; }
    async function fetchTrends() {
      const request = ++trendPageRequest;
      const company = globalEmpresa.value;
      trendPage.busy = true; trendPage.error = '';
      try {
        const data = await api('/api/telemetria/tendencias/?all=true' + (company ? '&empresa_id=' + company : ''));
        if (request !== trendPageRequest || company !== globalEmpresa.value) return;
        if (!Array.isArray(data)) throw new Error('Não foi possível carregar as tendências. Tente atualizar.');
        ++trendMonitorRequest; trendMonitor.busy = false;
        acceptTrendSnapshot(data);
        trendPage.rows = data;
        ensureTrendSelection();
        clampTrendPage();
        if (trendPage.detail) trendPage.detail = data.find(trend => trend.sensor_id === trendPage.detail.sensor_id) || null;
        trendPage.updatedAt = new Date().toISOString();
      } catch (error) {
        if (request === trendPageRequest) trendPage.error = error.message || 'Não foi possível carregar as tendências.';
      } finally {
        if (request === trendPageRequest) trendPage.busy = false;
      }
    }
    function clampTrendPage() {
      if (trendPage.offset >= trendCount.value) trendPage.offset = trendCount.value
        ? Math.floor((trendCount.value - 1) / trendPage.size) * trendPage.size : 0;
    }
    function applyTrendFilters(equipmentChanged = false) {
      trendPage.offset = 0; trendPage.detail = null;
      ensureTrendSelection(true);
    }
    function ensureTrendSelection(checkFilters = false) {
      const candidates = filteredTrends.value;
      if (!selectedTrend.value || (checkFilters && !candidates.some(t => t.sensor_id === Number(trendPage.sensor)))) {
        trendPage.sensor = candidates[0]?.sensor_id || '';
        trendPage.chartMode = 'live';
      }
    }
    function selectTrendEquipment(id, event) {
      trendPage.equipment = id; trendPage.equipmentSearch = '';
      if (event) {
        const picker = event.target.closest('details');
        picker.open = false; picker.querySelector('summary')?.focus();
      }
      applyTrendFilters(true);
    }
    function clearTrendFilters() {
      Object.assign(trendPage, { equipment: '', search: '', equipmentSearch: '', condition: '', offset: 0, detail: null });
      ensureTrendSelection(true);
    }
    function changeTrendPage(delta) {
      trendPage.offset = Math.max(0, trendPage.offset + delta * trendPage.size);
    }
    function openTrendDetail(trend) {
      if (Number(trendPage.sensor) !== trend.sensor_id) trendPage.chartMode = 'live';
      trendPage.sensor = trend.sensor_id; trendPage.listOpen = false;
    }
    function showTrends(equipment = '', sensor = '') {
      Object.assign(trendPage, { equipment, sensor, search: '', condition: '', chartMode: 'live', listOpen: false, offset: 0, detail: null });
      view.value = 'tendencias'; closeEquipModal(); return fetchTrends();
    }

    async function fetchHistorico() {
      await withLoading(async () => {
        const p = new URLSearchParams();
        if (filters.historico.search) p.set('search', filters.historico.search);
        if (filters.historico.data_de) p.set('data_execucao_depois', filters.historico.data_de);
        if (filters.historico.data_ate) p.set('data_execucao_antes', filters.historico.data_ate);
        if (globalEmpresa.value) p.set('ordem_servico__equipamento__empresa', globalEmpresa.value);
        const d = await api('/api/historico/?' + p);
        let items = normList(d);
        // Filtro local de custo (soma peças + mão de obra)
        if (filters.historico.custo_min) {
          const min = parseFloat(filters.historico.custo_min);
          items = items.filter(h => (parseFloat(h.custo_pecas) || 0) + (parseFloat(h.custo_mao_de_obra) || 0) >= min);
        }
        if (filters.historico.custo_max) {
          const max = parseFloat(filters.historico.custo_max);
          items = items.filter(h => (parseFloat(h.custo_pecas) || 0) + (parseFloat(h.custo_mao_de_obra) || 0) <= max);
        }
        lists.historico = items;
        Object.assign(pages.historico, normPages(d));
      });
    }

    async function fetchEmpresas() {
      await withLoading(async () => {
        const p = new URLSearchParams();
        if (filters.empresas.search) p.set('search', filters.empresas.search);
        const d = await api('/api/empresas/?' + p);
        lists.empresas = normList(d);
        Object.assign(pages.empresas, normPages(d));
      });
    }

    async function fetchUsuarios() {
      await withLoading(async () => {
        const p = new URLSearchParams();
        if (filters.usuarios.search) p.set('search', filters.usuarios.search);
        const d = await api('/api/usuarios/?' + p);
        const items = normList(d);
        sortByTipoUsuario(items);
        lists.usuarios = items;
        Object.assign(pages.usuarios, normPages(d));
      });
    }

    const osPrompt = reactive({ busy: false, saving: false, loaded: false, error: '', edit_text: '', original_text: '', is_customized: false });
    const promptCompanyId = computed(() => isAdmin.value ? globalEmpresa.value : me.value?.empresa);
    let osPromptRequest = 0;
    function clearOsPrompt() {
      ++osPromptRequest;
      Object.assign(osPrompt, { busy: false, saving: false, loaded: false, error: '', edit_text: '', original_text: '', is_customized: false });
    }
    function applyOsPrompt(data) {
      Object.assign(osPrompt, { loaded: true, edit_text: data.effective_text, original_text: data.original_text, is_customized: data.is_customized });
    }
    async function fetchPrompts() {
      clearOsPrompt();
      if (!isAdminOrGestor.value || !promptCompanyId.value) return;
      const request = osPromptRequest, company = promptCompanyId.value, actor = me.value?.id;
      const current = () => request === osPromptRequest && company === promptCompanyId.value && actor === me.value?.id;
      osPrompt.busy = true;
      try {
        const data = await api('/api/gemini/prompts/analise-os/?empresa=' + company);
        if (current() && data) applyOsPrompt(data);
      } catch {
        if (current()) osPrompt.error = 'Não foi possível carregar as instruções. Tente novamente.';
      } finally { if (current()) osPrompt.busy = false; }
    }
    async function saveOsPrompt(restore = false) {
      if (!isAdminOrGestor.value || !promptCompanyId.value || !osPrompt.loaded || osPrompt.busy || osPrompt.saving) return;
      const request = ++osPromptRequest, company = promptCompanyId.value, actor = me.value?.id;
      const current = () => request === osPromptRequest && company === promptCompanyId.value && actor === me.value?.id;
      osPrompt.saving = true; osPrompt.error = '';
      try {
        const text = osPrompt.edit_text.trim();
        const data = await api('/api/gemini/prompts/analise-os/' + (restore ? 'reset/' : '') + '?empresa=' + company, {
          method: restore ? 'POST' : 'PATCH',
          ...(restore ? {} : { body: JSON.stringify({ custom_text: text === osPrompt.original_text ? '' : text }) })
        });
        if (current() && data) { applyOsPrompt(data); toast(restore ? 'Instruções padrão restauradas.' : 'Instruções salvas.'); }
      } catch (error) {
        if (current()) osPrompt.error = parseDjangoErrors(error.fieldErrors).custom_text || error.fieldErrors?.detail || 'Não foi possível salvar as instruções. Tente novamente.';
      } finally { if (current()) osPrompt.saving = false; }
    }
    async function fetchLegacyPrompts() {
      if (!isAdmin.value) return;
      const actor = me.value?.id;
      try {
        const data = await api('/api/gemini/prompts/');
        if (isAdmin.value && me.value?.id === actor && data) lists.prompts = data.map(p => ({ ...p, edit_text: p.custom_text || p.original_text }));
      } catch { if (isAdmin.value && me.value?.id === actor) toast('Não foi possível carregar os outros prompts.', 'error'); }
    }
    function loadOtherPrompts(event) { if (event.target.open) fetchLegacyPrompts(); }

    async function savePrompt(promptId, customText) {
      try {
        await api(`/api/gemini/prompts/${promptId}/`, {
          method: 'PATCH',
          body: JSON.stringify({ custom_text: customText })
        });
        toast('Prompt salvo com sucesso!', 'success');
        await fetchLegacyPrompts();
      } catch (e) {
        toast('Erro ao salvar prompt', 'error');
      }
    }

    async function resetPrompt(promptId) {
      if (!confirm('Tem certeza que deseja restaurar o prompt original?')) return;
      try {
        await api(`/api/gemini/prompts/${promptId}/reset/`, { method: 'POST' });
        toast('Prompt restaurado para o original!', 'success');
        await fetchLegacyPrompts();
      } catch (e) {
        toast('Erro ao restaurar prompt', 'error');
      }
    }

    async function fetchLocalizacoes() {
      await withLoading(async () => {
        const p = new URLSearchParams();
        if (filters.localizacoes.search) p.set('search', filters.localizacoes.search);
        if (filters.localizacoes.setor) p.set('setor__icontains', filters.localizacoes.setor);
        const d = await api('/api/localizacao/?' + p);
        lists.localizacoes = normList(d);
        Object.assign(pages.localizacoes, normPages(d));
      });
    }

    async function fetchEmpresasAll() {
      if (isTecnico.value || lists.empresas.length) return;
      lists.empresas = await telemetryAll('/api/empresas/?limit=200');
    }
    async function fetchEquipamentosAll() {
      if (lists.equipamentos.length) return;
      const d = await api('/api/equipamentos/?limit=999');
      lists.equipamentos = normList(d);
    }
    async function fetchSensoresAll() {
      if (lists.sensores.length) return;
      const d = await api('/api/telemetria/sensores/?limit=999');
      lists.sensores = normList(d);
    }
    async function fetchOrdensAll() {
      if (!lists.usuarios.length) await fetchUsuariosAll();
      if (lists.ordens.length) return;
      const d = await api('/api/ordens-servico/?limit=999');
      lists.ordens = normList(d);
    }
    async function fetchUsuariosAll() {
      if (isTecnico.value || lists.usuarios.length) return;
      const d = await api('/api/usuarios/?limit=999');
      const items = normList(d);
      sortByTipoUsuario(items);
      lists.usuarios = items;
    }

    async function fetchPage(resource, url) {
      if (!url) return;
      if (resource === 'alertas') return fetchAlertas(url);
      if (resource === 'ordens') return fetchOrdens(url);
      await withLoading(async () => {
        const path = url.replace(/^https?:\/\/[^\/]+/, '');
        const d = await api(path);
        lists[resource] = normList(d);
        if (pages[resource]) Object.assign(pages[resource], normPages(d));
      });
    }

    // ─ Modal / CRUD ───────────────────────────────────
    const modalConfig = {
      equipamento: {
        title: 'Equipamento', endpoint: '/api/equipamentos/',
        defaults: { nome: '', tipo: '', modelo: '', fabricante: '', numero_serie: '', status: 'ativo', criticidade: null, justificativa_criticidade: '', aceitar_sugestao: false, tipo_equipamento: null, empresa: null, data_instalacao: '', descricao: '' }
      },

      ordem: {
        title: 'Ordem de Serviço', endpoint: '/api/ordens-servico/',
        defaults: { titulo: '', tipo_os: 'preventiva', gravidade_condicao: 'ausente', risco_seguranca: false, status: 'pendente', equipamento: null, responsavel: null, descricao: '', custo_pecas: null, custo_mao_de_obra: null }
      },
      encerrar_os: {
        title: 'Encerrar O.S.', endpoint: '/api/ordens-servico/',
        defaults: { titulo: '', tipo_os: 'preventiva', status: 'concluida', equipamento: null, responsavel: null, descricao: '', custo_pecas: null, custo_mao_de_obra: null }
      },

      empresa: {
        title: 'Empresa', endpoint: '/api/empresas/',
        defaults: { nome: '', cnpj: '', telefone: '', email: '', cidade: '', estado: '', endereco: '' }
      },
      sensor: {
        title: 'Sensor', endpoint: '/api/telemetria/sensores/',
        defaults: {
          nome: '', tipo: '', unidade_medida: '', equipamento: null, empresa: null, ativo: true,
          limite_alerta: null,
          limite_alerta_baixo_pct: 70.0,
          limite_alerta_medio_pct: 85.0,
          limite_alerta_critico_pct: 100.0,
        }
      },
      leitura: {
        title: 'Leitura de Telemetria', endpoint: '/api/telemetria/leituras/',
        defaults: { sensor: null, valor: '', timestamp: '' }
      },

      // AJUSTE: Campos alinhados com o Django (ordem_servico, custo_pecas, custo_mao_de_obra, etc)
      historico: {
        title: 'Histórico', endpoint: '/api/historico/',
        defaults: { ordem_servico: null, descricao_servico: '', custo_pecas: 0, custo_mao_de_obra: 0, data_execucao: '' }
      },

      usuario: {
        title: 'Usuário', endpoint: '/api/usuarios/',
        defaults: { username: '', email: '', first_name: '', last_name: '', tipo_usuario: 'tecnico', empresa: null, cargo: '', telefone: '' }
      },
      localizacao: {
        title: 'Localização', endpoint: '/api/localizacao/',
        defaults: { equipamento: null, setor: '' }
      },
      change_password: {
        title: 'Trocar Senha', endpoint: '/api/auth/change-password/',
        defaults: { senha_atual: '', nova_senha: '', confirmar_nova_senha: '' }
      },
    };

    function resetForm(defaults) {
      // Remove chaves que não existem nos novos defaults
      Object.keys(fd).forEach(k => { if (!(k in defaults)) delete fd[k]; });
      // Atribui individualmente para garantir reatividade correta no Vue 3
      const copy = JSON.parse(JSON.stringify(defaults));
      Object.keys(copy).forEach(k => { fd[k] = copy[k]; });
    }

    async function openModal(type, options = {}) {
      const cfg = modalConfig[type];
      modal.type = type; modal.title = 'Novo ' + cfg.title;
      modal.editId = null; modal.oldStatus = null; formErrors.value = {};
      resetForm(cfg.defaults);

      if (type === 'leitura') {
        const selectedSensorId = options.sensor || dashTelemetriaSensor.value;
        if (selectedSensorId) {
          fd.sensor = Number(selectedSensorId);
        }
      }

      if (type === 'equipamento') fd.empresa = globalEmpresa.value ? Number(globalEmpresa.value) : me.value?.empresa || null;
      modal.open = true;
      if (type === 'equipamento') await loadEquipmentGuide();
      if (['equipamento', 'ordem', 'sensor', 'localizacao', 'leitura'].includes(type)) {
        await fetchEquipamentosAll();
        await fetchEmpresasAll();
      }
      if (type === 'ordem') {
        await fetchUsuariosAll();
        const company = globalEmpresa.value || me.value?.empresa;
        orderEquipmentOptions.value = await telemetryAll('/api/equipamentos/?limit=100' + (company ? '&empresa=' + company : ''));
      }
      if (type === 'leitura') await fetchSensoresAll();
      if (type === 'usuario') await fetchEmpresasAll();
      if (type === 'historico') await fetchOrdensAll(); // Histórico precisa das ordens
    }

    async function editItem(type, item) {
      const cfg = modalConfig[type];
      modal.type = type; modal.title = 'Editar ' + cfg.title;
      modal.editId = item.id; modal.oldStatus = item.status; formErrors.value = {};
      resetForm({ ...cfg.defaults, ...item }); modal.open = true;
      if (type === 'equipamento') await loadEquipmentGuide();

      if (['equipamento', 'ordem', 'sensor', 'localizacao', 'leitura'].includes(type)) {
        await fetchEquipamentosAll();
        await fetchEmpresasAll();
      }
      if (type === 'ordem') {
        await fetchUsuariosAll();
        const company = globalEmpresa.value || me.value?.empresa;
        orderEquipmentOptions.value = await telemetryAll('/api/equipamentos/?limit=100' + (company ? '&empresa=' + company : ''));
      }
      if (type === 'leitura') await fetchSensoresAll();
      if (type === 'usuario') await fetchEmpresasAll();
      if (type === 'historico') await fetchOrdensAll();
    }

    async function saveItem() {
      const cfg = modalConfig[modal.type];
      modal.saving = true; formErrors.value = {};
      try {
        const payload = { ...fd };

        // Limpa FKs vazias
        ['empresa', 'equipamento', 'sensor', 'ordem_servico', 'responsavel'].forEach(k => {
          if (payload[k] === '' || payload[k] === 0) payload[k] = null;
        });

        // Garante valores válidos para campos choice da OS
        if (modal.type === 'ordem' || modal.type === 'encerrar_os') {
          if (payload.status === 'concluida' && !payload.responsavel && me.value?.id) {
            payload.responsavel = me.value.id;
          }
          const statusValidos = ['pendente', 'andamento', 'concluida', 'cancelada'];
          const tiposValidos = ['preventiva', 'corretiva', 'preditiva'];
          for (const key of ['prioridade', 'prioridade_automatica', 'prioridade_manual', 'prioridade_origem', 'prioridade_herdada_conhecida', 'justificativa_prioridade', 'criticidade_na_abertura', 'justificativa_criticidade_na_abertura', 'criterios_criticidade_na_abertura']) delete payload[key];
          if (!statusValidos.includes(payload.status)) payload.status = 'pendente';
          if (!tiposValidos.includes(payload.tipo_os)) payload.tipo_os = 'preventiva';
        }

        // Se for encerrar O.S., mesclar o relato do técnico na descrição
        if (modal.type === 'encerrar_os') {
          const relato = fd.descricao_servico_realizado?.trim();
          if (!relato) {
            toast('Por favor, preencha o campo de serviço realizado.', 'error');
            modal.saving = false;
            return;
          }
          // Concatena a descrição original + relato do técnico
          const original = fd._descricao_original || '';
          payload.descricao = original
            ? `${original}\n\n--- Serviço realizado (${new Date().toLocaleDateString('pt-BR')}) ---\n${relato}`
            : relato;
          // Remove campos internos
          delete payload._descricao_original;
          delete payload.descricao_servico_realizado;
        }

        let createdOsId = modal.editId;
        if (modal.editId) {
          const saved = await api(cfg.endpoint + modal.editId + '/', {
            method: 'PUT',
            body: JSON.stringify(payload),
          });
          if (modal.type === 'ordem' || modal.type === 'encerrar_os') syncOrderDetails(saved);
        } else {
          const res = await api(cfg.endpoint, { method: 'POST', body: JSON.stringify(payload) });
          if ((modal.type === 'ordem' || modal.type === 'encerrar_os') && res) createdOsId = res.id;
        }

        if (modal.type === 'equipamento' && equipModal.open && equipModal.equipamento?.id === modal.editId) {
          equipModal.equipamento = await api('/api/equipamentos/' + modal.editId + '/');
          await loadEquipmentAssessment(equipModal.equipamento);
        }
        modal.open = false;
        toast(modal.type === 'change_password' ? 'Senha alterada com sucesso!' : (modal.editId ? 'Atualizado com sucesso!' : 'Criado com sucesso!'), 'success');
        if (modal.type === 'leitura') {
          await Promise.all([
            fetchDashboard(),
            fetchOrdens(),
          ]);
        }
        navigate(view.value);
      } catch (e) {
        if (e.fieldErrors) {
          formErrors.value = parseDjangoErrors(e.fieldErrors);
          const fields = Object.keys(formErrors.value).filter(k => k !== '_global');
          if (fields.length) toast('Preencha os campos obrigatórios: ' + fields.join(', '), 'error');
          else if (formErrors.value._global) toast(formErrors.value._global, 'error');
        } else { toast('Erro inesperado: ' + e.message, 'error'); }
      } finally { modal.saving = false; }
    }

    async function deleteItem(endpoint, id) {
      if (!confirm('Confirmar exclusão?')) return;
      try {
        await api('/api/' + endpoint + '/' + id + '/', { method: 'DELETE' });
        toast('Excluído com sucesso!', 'success');
        navigate(view.value);
      } catch { toast('Erro ao excluir', 'error'); }
    }

    async function assumirOS(o) {
      if (!me.value?.id) return;
      if (o._assumindo) return;
      if (!confirm('Deseja assumir esta Ordem de Serviço?')) return;
      o._assumindo = true;
      const payload = { responsavel: me.value.id };
      if (o.status === 'pendente') payload.status = 'andamento';
      try {
        const saved = await api('/api/ordens-servico/' + o.id + '/', { method: 'PATCH', body: JSON.stringify(payload) });
        toast('O.S. assumida com sucesso!', 'success');
        o.responsavel = me.value.id;
        if (payload.status) o.status = payload.status;
        o.responsavel_nome = me.value.first_name || me.value.username || 'Você';
        syncOrderDetails(saved || o);
      } catch(e) {
        toast('Erro ao assumir O.S.', 'error');
        return;
      } finally {
        o._assumindo = false;
      }

      if (!lists.usuarios.length) {
        try {
          await fetchUsuariosAll();
        } catch (err) {
          console.warn('Falha ao carregar usuários:', err);
        }
      }
    }

    async function iniciarAtendimento(o) {
      if (!me.value?.id) return;
      if (o._assumindo) return;
      o._assumindo = true;
      const payload = { responsavel: me.value.id, status: 'andamento' };
      try {
        const saved = await api('/api/ordens-servico/' + o.id + '/', { method: 'PATCH', body: JSON.stringify(payload) });
        toast('Atendimento iniciado!', 'success');
        o.responsavel = me.value.id;
        o.status = 'andamento';
        syncOrderDetails(saved || o);
      } catch(e) {
        toast('Erro ao iniciar atendimento.', 'error');
        return;
      } finally {
        o._assumindo = false;
      }
    }

    async function openEncerrarOS(item) {
      await editItem('ordem', item);
      modal.type = 'encerrar_os';
      modal.title = 'Encerrar Ordem de Serviço';
      fd.status = 'concluida';
      // Salva a descrição original como histórico read-only
      fd._descricao_original = item.descricao || '';
      // Campo separado para o relato do técnico (começa vazio)
      fd.descricao_servico_realizado = '';
      if (!fd.responsavel && me.value?.id) {
        fd.responsavel = me.value.id;
      }
    }

    // ─ Exportação (com fallback client-side) ─────────
    function getExportData(resource) {
      const now = new Date().toLocaleString('pt-BR');
      switch (resource) {
        case 'equipamentos':
          return {
            title: 'Equipamentos',
            subtitle: `Gerado em: ${now}`,
            columns: ['ID', 'Nome', 'Modelo', 'Fabricante', 'Nº Série', 'Setor', 'Status', 'Empresa'],
            rows: lists.equipamentos.map(e => [
              e.id, e.nome, e.modelo || '—', e.fabricante || '—',
              e.numero_serie || '—', locSetor(e.id), e.status || '—', empresaNome(e.empresa)
            ])
          };
        case 'alertas':
          return {
            title: 'Histórico de alertas',
            subtitle: `Gerado em: ${now}`,
            columns: ['ID', 'Tipo', 'Nível máximo', 'Motivo', 'Equipamento', 'Normalização', 'Data', 'Sensor', 'Origem', 'O.S.'],
            rows: lists.alertas.map(a => [
              a.id, a.tipo_alerta, a.nivel, a.dados_deteccao?.descricao || a.descricao || '—',
              a.equipamento_nome || eqNome(a.equipamento), fmtDate(a.data_normalizacao), fmtDate(a.data_alerta),
              a.sensor_nome || '—', a.origem, a.ordem_servico_id || '—'
            ])
          };
        case 'ordens-servico':
          return {
            title: 'Ordens de Serviço',
            subtitle: `Gerado em: ${now}`,
            columns: ['ID', 'Título', 'Tipo', 'Prioridade', 'Status', 'Equipamento', 'Data Abertura'],
            rows: lists.ordens.map(o => [
              o.id, o.titulo, o.tipo_os || '—', o.prioridade || '—',
              o.status || '—', eqNome(o.equipamento), fmtDate(o.data_abertura || o.criado_em)
            ])
          };
        case 'historico':
          return {
            title: 'Histórico de Manutenção',
            subtitle: `Gerado em: ${now}`,
            columns: ['ID', 'OS', 'Descrição', 'Custo Peças (R$)', 'Custo M.O. (R$)', 'Total (R$)', 'Data Execução'],
            rows: lists.historico.map(h => [
              h.id, `#${h.ordem_servico}`, h.descricao_servico || '—',
              h.custo_pecas != null ? Number(h.custo_pecas).toFixed(2) : '—',
              h.custo_mao_de_obra != null ? Number(h.custo_mao_de_obra).toFixed(2) : '—',
              custoTotal(h), h.data_execucao || '—'
            ])
          };
        case 'telemetria':
          return {
            title: 'Telemetria — Leituras de Sensores',
            subtitle: `Gerado em: ${now}`,
            columns: ['ID', 'Sensor', 'Valor', 'Data/Hora'],
            rows: lists.leituras.map(l => [
              l.id, sensorNome(l.sensor), l.valor, fmtDate(l.timestamp)
            ])
          };
        case 'dashboard': {
          const k = kpis.value;
          if (!k) return null;
          const rows = [
            ['Total de Equipamentos', k.total_equipamentos ?? '—'],
            ['Alertas nas últimas 24h', k.alertas_24h ?? '—'],
            ['Ordens Abertas', k.ordens_abertas ?? '—'],
            ['Leituras de Telemetria', k.leituras_hoje ?? '—'],
          ];
          if (chartEquipStatus.value.length) {
            rows.push(['', '']);
            rows.push(['── STATUS EQUIPAMENTOS ──', '']);
            chartEquipStatus.value.forEach(s => rows.push([s.label, s.value]));
          }
          if (chartAlertNivel.value.length) {
            rows.push(['', '']);
            rows.push(['── ALERTAS POR NÍVEL ──', '']);
            chartAlertNivel.value.forEach(a => rows.push([a.label, a.value]));
          }
          if (chartOrdens.value.length) {
            rows.push(['', '']);
            rows.push(['── ORDENS POR STATUS ──', '']);
            chartOrdens.value.forEach(o => rows.push([o.label, o.value]));
          }
          return {
            title: 'Dashboard — Resumo de KPIs',
            subtitle: `Gerado em: ${now}`,
            columns: ['Indicador', 'Valor'],
            rows
          };
        }
        default:
          return null;
      }
    }

    function triggerDownload(blob, filename) {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    }

    function exportCSVClientSide(data, resource) {
      const bom = '\uFEFF';
      const csvContent = [data.columns, ...data.rows]
        .map(row => row.map(cell => {
          const str = String(cell == null ? '' : cell);
          if (str.includes(',') || str.includes('"') || str.includes('\n')) {
            return '"' + str.replace(/"/g, '""') + '"';
          }
          return str;
        }).join(','))
        .join('\n');
      const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' });
      triggerDownload(blob, `${resource}.csv`);
    }

    function exportExcelClientSide(data, resource) {
      if (typeof XLSX === 'undefined') {
        toast('Biblioteca Excel não carregada. Recarregue a página e tente novamente.', 'error');
        return;
      }
      const wsData = [data.columns, ...data.rows];
      const ws = XLSX.utils.aoa_to_sheet(wsData);
      // Auto-width columns
      ws['!cols'] = data.columns.map((col, i) => {
        let maxLen = col.length;
        data.rows.forEach(row => {
          const cellLen = String(row[i] || '').length;
          if (cellLen > maxLen) maxLen = cellLen;
        });
        return { wch: Math.min(maxLen + 4, 50) };
      });
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, data.title.substring(0, 31));
      XLSX.writeFile(wb, `${resource}.xlsx`);
    }

    function exportPDFClientSide(data, resource) {
      if (typeof window.jspdf === 'undefined') {
        toast('Biblioteca PDF não carregada. Recarregue a página e tente novamente.', 'error');
        return;
      }
      const { jsPDF } = window.jspdf;
      const doc = new jsPDF('l', 'mm', 'a4');
      // Header
      doc.setFontSize(16);
      doc.setTextColor(46, 64, 87);
      doc.text(`NanaSmart \u2014 ${data.title}`, 14, 15);
      doc.setFontSize(9);
      doc.setTextColor(136, 136, 136);
      doc.text(data.subtitle, 14, 22);
      // Table
      doc.autoTable({
        head: [data.columns],
        body: data.rows.map(row => row.map(cell => String(cell ?? '—'))),
        startY: 28,
        theme: 'grid',
        headStyles: {
          fillColor: [46, 64, 87],
          textColor: 255,
          fontStyle: 'bold',
          fontSize: 7,
          cellPadding: 3,
        },
        bodyStyles: {
          fontSize: 7,
          cellPadding: 2,
        },
        alternateRowStyles: {
          fillColor: [242, 246, 250],
        },
        styles: {
          overflow: 'linebreak',
          lineColor: [204, 204, 204],
          lineWidth: 0.25,
        },
        margin: { left: 15, right: 15 },
      });
      // Footer
      const pageHeight = doc.internal.pageSize.height;
      doc.setFontSize(8);
      doc.setTextColor(153, 153, 153);
      doc.text(`Total de registros: ${data.rows.length}`, 15, pageHeight - 10);
      doc.save(`${resource}.pdf`);
    }

    async function exportData(resource, format) {
      toast(`Gerando exportação ${format.toUpperCase()}...`, 'success');

      // Build query params for backend API
      const p = new URLSearchParams();
      if (resource === 'equipamentos') {
        if (filters.equipamentos.status) p.set('status', filters.equipamentos.status);
        if (filters.equipamentos.empresa || globalEmpresa.value) p.set('empresa', filters.equipamentos.empresa || globalEmpresa.value);
      } else if (resource === 'alertas') {
        try { for (const [key, value] of alertParams()) p.set(key, value); }
        catch (error) { toast(error.message, 'error'); return; }
      } else if (resource === 'ordens-servico') {
        for (const [key, value] of orderParams()) p.set(key, value);
      } else if (resource === 'historico') {
        if (filters.historico.data_de) p.set('data_execucao_depois', filters.historico.data_de);
        if (filters.historico.data_ate) p.set('data_execucao_antes', filters.historico.data_ate);
        if (globalEmpresa.value) p.set('empresa', globalEmpresa.value);
      } else if (resource === 'telemetria') {
        if (globalEmpresa.value) p.set('empresa', globalEmpresa.value);
      } else if (resource === 'dashboard') {
        if (dashSetor.value) p.set('setor', dashSetor.value);
        if (dashEquipamento.value) p.set('equipamento_id', dashEquipamento.value);
        if (globalEmpresa.value) p.set('empresa_id', globalEmpresa.value);
      }

      // 1) Try backend API first
      try {
        const headers = {};
        if (token.value) headers['Authorization'] = `Bearer ${token.value}`;

        const res = await fetch(BASE + `/api/exportar/${resource}/${format}/?` + p.toString(), { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const blob = await res.blob();
        // Check if the response is actually a file, not a JSON error
        if (blob.size < 100 && blob.type && blob.type.includes('application/json')) {
          throw new Error('Backend returned error JSON');
        }

        let filename = `${resource}.${format === 'excel' ? 'xlsx' : format}`;
        const cd = res.headers.get('Content-Disposition');
        if (cd && cd.includes('filename=')) {
          filename = cd.split('filename=')[1].replace(/"/g, '').trim();
        }

        triggerDownload(blob, filename);
        return; // Backend export succeeded
      } catch (backendErr) {
        console.error('Exportação via backend falhou:', backendErr);
        toast('Não foi possível gerar a exportação. Tente novamente.', 'error');
      }
    }

    // ─ Helpers ───────────────────────────────────────
    function fmtDate(d) {
      if (!d) return '—';
      const date = new Date(d);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      
      const timeStr = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
      
      if (date.toDateString() === today.toDateString()) {
        return `Hoje, às ${timeStr}`;
      } else if (date.toDateString() === yesterday.toDateString()) {
        return `Ontem, às ${timeStr}`;
      }
      return date.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    }
    function formatNumber(value) {
      if (value == null || value === '') return '—';
      return Number(value).toLocaleString('pt-BR');
    }
    function nivelBadge(n) { return { critico: 'badge-red', medio: 'badge-yellow', baixo: 'badge-green' }[n] || 'badge-gray'; }
    function nivelColor(n) { return { critico: 'var(--signal)', medio: 'var(--warn)', baixo: 'var(--teal)' }[n] || 'var(--ink4)'; }
    function statusBadge(s) { return { ativo: 'badge-blue', resolvido: 'badge-green', ignorado: 'badge-gray' }[s] || 'badge-gray'; }
    function eqStatusBadge(s) { return { ativo: 'badge-green', manutencao: 'badge-yellow', inativo: 'badge-gray' }[s] || 'badge-gray'; }
    function ordemStatusBadge(s) { return { pendente: 'badge-blue', andamento: 'badge-yellow', concluida: 'badge-green', cancelada: 'badge-gray' }[s] || 'badge-gray'; }

    // AJUSTE: Classes baseadas nas novas prioridades do Django
    function prioridadeBadge(p) { return { A: 'badge-red', B: 'badge-yellow', C: 'badge-green', critica: 'badge-red', alta: 'badge-orange', media: 'badge-yellow', baixa: 'badge-green' }[p] || 'badge-gray'; }
    function prioridadeIcon(p) { return { A: '🔴', B: '🟡', C: '🟢', critica: '🔴', alta: '🟠', media: '🟡', baixa: '🟢' }[p] || '⚪'; }
    function prioridadeLabel(p) { return { A: 'A · Alta', B: 'B · Média', C: 'C · Baixa', critica: 'Crítica', alta: 'Alta', media: 'Média', baixa: 'Baixa' }[p] || 'A definir'; }

    function makeLineChart(readings, W = 360, H = 180, limit = 20, bounds = []) {
      const raw = Array.isArray(readings) ? readings.slice(0, limit).reverse() : [];
      if (!raw.length) return { path: '', area: '', dots: [], ticks: [], min: 0, max: 0 };
      const values = raw.map(l => parseFloat(l.valor) || 0);
      const min = Math.min(...values, ...bounds);
      const max = Math.max(...values, ...bounds);
      const range = max - min || 1;
      const points = values.map((v, i) => ({
        x: (i / (values.length - 1 || 1)) * W,
        y: H - ((v - min) / range) * H * 0.8 - H * 0.1,
        v,
        label: v.toFixed(2),
      }));
      const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
      const area = points.length ? `${path} L${W},${H} L0,${H} Z` : '';
      const ticks = [0, 1 / 3, 2 / 3, 1].map(f => {
        const y = H - f * H * 0.8 - H * 0.1;
        const value = (min + f * (max - min)).toFixed(2);
        return { y, label: value };
      });
      return { path, area, dots: points, ticks, min: min.toFixed(2), max: max.toFixed(2), lowValue: min, highValue: max };
    }

    async function fetchEquipamentoSensors(eqId) {
      equipModal.loading = true;
      equipModal.error = '';
      try {
        const res = await api(`/api/telemetria/sensores/?equipamento=${eqId}&limit=100`);
        equipModal.sensors = normList(res);
      } catch (err) {
        equipModal.sensors = [];
        equipModal.error = 'Falha ao carregar sensores do equipamento.';
        console.error('Erro fetchEquipamentoSensors:', err);
      } finally {
        equipModal.loading = false;
      }
    }

    async function fetchEquipamentoReadings(sensorId = equipModal.selectedSensor, options = { silent: false }) {
      if (!sensorId) {
        equipModal.readings = [];
        return;
      }
      const { silent } = options;
      if (!silent || !equipModal.readings.length) {
        equipModal.loading = true;
      } else {
        equipModal.refreshing = true;
      }
      equipModal.error = '';
      try {
        const res = await api(`/api/telemetria/leituras/?sensor=${sensorId}&limit=50&ordering=-timestamp`);
        if (res == null) {
          throw new Error('Resposta vazia da API de leituras.');
        }
        equipModal.readings = normList(res);
        equipModal.lastRefresh = new Date().toISOString();
      } catch (err) {
        if (!silent) {
          equipModal.readings = [];
        }
        equipModal.error = `Falha ao carregar leituras do sensor. ${err?.message || ''}`.trim();
        console.error('Erro fetchEquipamentoReadings:', err);
      } finally {
        equipModal.loading = false;
        equipModal.refreshing = false;
      }
    }

    async function fetchEquipamentoOrdens(eqId) {
      try {
        const res = await api(`/api/ordens-servico/?equipamento=${eqId}&limit=999`);
        equipModal.ordens = normList(res);

      } catch (err) {
        equipModal.ordens = [];
        console.error("Erro ao buscar ordens do equipamento", err);
      }
    }

    async function pollEquipamentoReadings() {
      if (!equipModal.open || !equipModal.selectedSensor) return;
      await Promise.all([fetchEquipamentoReadings(equipModal.selectedSensor, { silent: true }), fetchTrendForSensor(equipModal.selectedSensor)]);
      if (equipModal.open && equipModal.selectedSensor) {
        equipModalPollTimer = window.setTimeout(pollEquipamentoReadings, 5000);
      }
    }

    function stopEquipModalPolling() {
      if (equipModalPollTimer) {
        window.clearTimeout(equipModalPollTimer);
        equipModalPollTimer = null;
      }
    }

    async function openEquipamentoDetails(eq) {
      stopEquipModalPolling();
      equipModal.open = true;
      let equipment = (typeof eq === 'number' || typeof eq === 'string')
        ? lists.equipamentos.find(item => item.id === Number(eq)) || { id: Number(eq) }
        : eq;
      if (equipment && !equipment.nome) {
        try {
          equipment = await api(`/api/equipamentos/${equipment.id}/`);
        } catch (err) {
          console.warn('Não foi possível obter detalhes completos do equipamento:', err);
        }
      }
      equipModal.equipamento = equipment;
      loadEquipmentAssessment(equipment);
      equipModal.selectedSensor = null;
      equipModal.readings = [];
      equipModal.error = '';
      equipModal.refreshing = false;
      equipModal.ordens = [];
      equipModal.osFilter = 'todas';
      await fetchEquipamentoSensors(equipment.id);
      fetchEquipamentoOrdens(equipment.id);
      if (equipModal.sensors.length) {
        equipModal.selectedSensor = equipModal.sensors[0].id;
      }
      pollEquipamentoReadings();
    }

    function closeEquipModal() {
      ++assessmentRequest; equipmentAssessment.history = []; equipmentAssessment.busy = false;
      equipModal.open = false;
      equipModal.equipamento = null;
      equipModal.sensors = [];
      equipModal.selectedSensor = null;
      equipModal.readings = [];
      equipModal.error = '';
      equipModal.lastRefresh = null;
      equipModal.loading = false;
      equipModal.refreshing = false;
      equipModal.ordens = [];
      stopEquipModalPolling();
    }

    watch(() => equipModal.selectedSensor, async (sensorId) => {
      if (sensorId && equipModal.open) {
        await Promise.all([fetchEquipamentoReadings(sensorId), fetchTrendForSensor(sensorId)]);
        stopEquipModalPolling();
        pollEquipamentoReadings();
      }
    });

    function eqNome(id) {
      if (id == null) return '—';
      const eq = lists.equipamentos.find(e => e.id === id) || dashboardEquipamentos.value.find(e => e.id === Number(id));
      return eq ? `${eq.nome} (#${eq.id})` : `#${id}`;
    }
    function getEquipamentoInfo(id) {
      if (id == null) return null;
      return lists.equipamentos.find(e => e.id === id) || null;
    }
    function osTitulo(id) {
      if (id == null) return '—';
      const os = lists.ordens.find(o => o.id === id);
      return os ? os.titulo : '—';
    }
    function osEquipNome(id) {
      if (id == null) return '—';
      const os = lists.ordens.find(o => o.id === id);
      return os ? eqNome(os.equipamento) : '—';
    }
    function empresaNome(id) {
      if (id == null) return '—';
      const e = lists.empresas.find(e => e.id === id);
      return e ? e.nome : `#${id}`;
    }
    function sensorNome(id) {
      if (id == null) return '—';
      const s = lists.sensores.find(s => s.id === id);
      return s ? `${s.nome} (#${s.id})` : `#${id}`;
    }
    function locSetor(eqId) {
      if (eqId == null) return '—';
      const loc = lists.localizacoes.find(l => l.equipamento === eqId);
      return loc ? (loc.setor || '—') : '—';
    }
    function custoTotal(h) {
      return ((parseFloat(h.custo_pecas) || 0) + (parseFloat(h.custo_mao_de_obra) || 0)).toFixed(2);
    }
    function countSensores(eqId) {
      if (eqId == null) return 0;
      return lists.sensores.filter(s => getEquipamentoId(s.equipamento) === eqId).length;
    }
    function usuarioNome(id) {
      if (!id) return '';
      const userId = typeof id === 'object' ? id.id : id;
      const u = lists.usuarios.find(x => x.id === userId);
      if (u) return u.username;
      if (me.value?.id === userId) return me.value.username;
      return '';
    }
    function eqEmpresaNome(eqId) {
      if (!eqId) return '—';
      const eq = lists.equipamentos.find(e => e.id === eqId);
      if (!eq || !eq.empresa) return '—';
      return empresaNome(eq.empresa);
    }
    function empresaNomeSensor(s) {
      const equipamentoId = getEquipamentoId(s.equipamento);
      if (!equipamentoId) return '—';
      const eq = lists.equipamentos.find(e => e.id === equipamentoId);
      if (!eq || !eq.empresa) return '—';
      return empresaNome(eq.empresa);
    }
    function sensorEquipNome(sensorId) {
      if (!sensorId) return '—';
      const s = lists.sensores.find(x => x.id === sensorId);
      const equipamentoId = getEquipamentoId(s?.equipamento);
      if (!s || !equipamentoId) return '—';
      return eqNome(equipamentoId);
    }

    function computeSensorThresholds(sensor) {
      if (!sensor) return null;
      const limit = parseFloat(sensor.limite_alerta) || 0;
      const lowPct = sensor.limite_alerta_baixo_pct !== undefined && sensor.limite_alerta_baixo_pct !== null ? parseFloat(sensor.limite_alerta_baixo_pct) : 70;
      const medPct = sensor.limite_alerta_medio_pct !== undefined && sensor.limite_alerta_medio_pct !== null ? parseFloat(sensor.limite_alerta_medio_pct) : 85;
      const critPct = sensor.limite_alerta_critico_pct !== undefined && sensor.limite_alerta_critico_pct !== null ? parseFloat(sensor.limite_alerta_critico_pct) : 100;
      return {
        limit,
        unit: sensor.unidade_medida || '',
        lowPct,
        medPct,
        critPct,
        lowValue: limit ? (limit * lowPct / 100).toFixed(2) : '—',
        medValue: limit ? (limit * medPct / 100).toFixed(2) : '—',
        critValue: limit ? (limit * critPct / 100).toFixed(2) : '—',
      };
    }

    const selectedSensorThresholds = computed(() => {
      return computeSensorThresholds(selectedEquipSensor.value);
    });

    const sensorModalThresholds = computed(() => {
      if (modal.type !== 'sensor') return null;
      const sensor = {
        limite_alerta: fd.limite_alerta,
        limite_alerta_baixo_pct: fd.limite_alerta_baixo_pct,
        limite_alerta_medio_pct: fd.limite_alerta_medio_pct,
        limite_alerta_critico_pct: fd.limite_alerta_critico_pct,
        unidade_medida: fd.unidade_medida,
      };
      return computeSensorThresholds(sensor);
    });

    function onGlobalEmpresaChange() {
      closeABC(); closeEquipModal();
      ++dashboardRequest; dashboardKpisLoading.value = false; dashboardSummary.value = null; dashboardUpdatedAt.value = null; dashSetor.value = ''; dashEquipamento.value = ''; performanceOpen.value = false; liveOpen.value = false;
      clearTrendDemo(); resetTrendMonitoring();
      ++dashboardSummaryRequest; dashboardSummary.value = null; dashAlerts.value = []; alertCount.value = 0;
      ++alertRequest; closeAlertaDetails(); lists.alertas = []; alertHistory.url = ''; alertHistory.count = 0;
      Object.assign(filters.alertas, { search: '', nivel: '', origem: '', equipamento: '', sensor: '', from: '', to: '' });
      ++telemetryRequest; ++telemetryOptionsRequest; ++trendPageRequest;
      Object.assign(telemetry, { equipment: '', sensor: '', offset: 0, rows: [], equipments: [], sensors: [], busy: false });
      Object.assign(trendPage, { equipment: '', sensor: '', search: '', equipmentSearch: '', chartMode: 'live', listOpen: false, condition: '', offset: 0, rows: [], detail: null, busy: false, updatedAt: null, error: '' });
      // Recarrega a aba atual ao mudar o filtro global
      // Também recarrega o dashboard se estiver nele
      const currentView = view.value;
      if (currentView === 'dashboard') {
        fetchDashboard();
      } else {
        fetchers[currentView]?.();
        if (currentView !== 'tendencias') fetchTrendAlerts();
      }
    }

    // ─── ATUALIZAÇÃO AUTOMÁTICA SILENCIOSA (OTIMIZADA) ───
    onMounted(async () => {
      // Adicionar listener para fechar janelas com ESC
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          if (priorityModal.open) { priorityModal.open = false; ++priorityRequest; }
          else if (criteriaModal.open) { criteriaModal.open = false; ++criteriaRequest; }
          else if (trendConfigModal.open) closeTrendConfig();
          else if (trendPage.detail && view.value === 'tendencias') trendPage.detail = null;
          else if (modal.open) modal.open = false;
          else if (equipModal.open) closeEquipModal();
          else if (chatOpen.value) chatOpen.value = false;
        }
      });

      if (token.value) {
        await fetchMe();
        // Carrega lista de empresas para o filtro global do admin
        await fetchEmpresasAll();
        navigate('dashboard');
        startTrendPolling();
      }
      document.addEventListener('visibilitychange', onTrendVisibilityChange);

      dashboardTimer = setInterval(() => {
        if (token.value && !document.hidden && view.value === 'dashboard') fetchDashboard({ silent: true });
      }, 30000);
    });

    function onTrendVisibilityChange() {
      if (!document.hidden) { refreshTrendMonitoring(); if (token.value && view.value === 'dashboard') fetchDashboard({ silent: true }); }
    }
    onUnmounted(() => {
      closeOrderDetails();
      if (dashboardTimer !== null) clearInterval(dashboardTimer); ++dashboardRequest;
      stopTrendPolling(); stopDemoPolling(); ++demoRequest; ++trendMonitorRequest;
      document.removeEventListener('visibilitychange', onTrendVisibilityChange);
    });

    // As janelas de edição, prioridade e equipamento devolvem o foco à O.S.
    watch(() => [modal.open, priorityModal.open, equipModal.open, !!alertHistory.detail], (current, previous) => {
      if (orderDetail.open && previous?.some(Boolean) && !current.some(Boolean)) focusOrderDetails();
    });

    // ─ Chat AI (NanaSmart AI) ────────────────────────
    // Este widget usa o token JWT armazenado em localStorage e o usuário atual
    // carregado via /api/auth/me/. Assim o backend escolhe o contexto correto
    // e encaminha a requisição ao endpoint de Gemini apropriado para o papel.
    const chatOpen = ref(false);
    const chatExpanded = ref(false);
    const chatAtBottom = ref(true);
    const chatInput = ref('');
    const chatInputField = ref(null);
    const chatLoading = ref(false);
    const chatMessages = ref([
      {
        role: 'ai',
        text: 'Olá! Sou a **NanaSmart AI**, assistente virtual especializada em confiabilidade e engenharia de manutenção preditiva da planta. Posso te ajudar a analisar métricas como MTBF, MTTR, disponibilidade, sensores IoT e o status das ordens de serviço. Como posso auxiliar você hoje?'
      }
    ]);
    const chatScrollContainer = ref(null);

    const chatMode = computed(() => {
      if (!me.value || !me.value.tipo_usuario) return 'chat';
      if (me.value.tipo_usuario === 'tecnico') return 'os_analysis';
      if (me.value.tipo_usuario === 'gestor') return 'finance';
      if (me.value.tipo_usuario === 'admin') return 'chat';
      return 'chat';
    });

    const chatPlaceholder = computed(() => {
      if (chatMode.value === 'os_analysis') return 'Descreva a situação da ordem de serviço ou problema do equipamento...';
      if (chatMode.value === 'finance') return 'Peça orientação de gestão de manutenção e redução de custos...';
      return 'Pergunte sobre o parque, alertas ou desempenho da manutenção...';
    });

    function getChatEndpointPath() {
      if (chatMode.value === 'os_analysis') return '/api/gemini/ordens/analise/';
      if (chatMode.value === 'finance') return '/api/gemini/gestao/financeira/';
      return '/api/gemini/chat/';
    }

    function toggleChat() {
      chatOpen.value = !chatOpen.value;
      if (chatOpen.value) {
        scrollToBottom();
      }
    }

    function toggleChatExpand() {
      chatExpanded.value = !chatExpanded.value;
      nextTick(() => {
        scrollToBottom();
        resizeChatInput();
      });
    }

    function resizeChatInput() {
      nextTick(() => {
        if (!chatInputField.value) return;
        const el = chatInputField.value;
        el.style.height = 'auto';
        el.style.height = Math.min(el.scrollHeight, 200) + 'px';
      });
    }

    function handleChatKeydown(event) {
      if (event.key !== 'Enter') return;
      if (event.shiftKey) return;
      event.preventDefault();
      sendChatMessage();
    }

    function setChatScrollState() {
      if (!chatScrollContainer.value) return;
      const el = chatScrollContainer.value;
      chatAtBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 20;
    }

    function onChatScroll() {
      setChatScrollState();
    }

    function scrollToBottom() {
      nextTick(() => {
        if (chatScrollContainer.value) {
          const el = chatScrollContainer.value;
          el.scrollTop = el.scrollHeight;
          chatAtBottom.value = true;
        }
      });
    }

    async function sendChatMessage() {
      const msgText = chatInput.value.trim();
      if (!msgText || chatLoading.value) return;

      if (chatMode.value === 'finance' && me.value?.tipo_usuario === 'tecnico') {
        chatMessages.value.push({
          role: 'ai',
          text: 'O modo de gestão financeira está disponível apenas para gestores e administradores. Use o chat geral ou análise de ordens.'
        });
        chatInput.value = '';
        return;
      }

      // Adiciona mensagem do usuário
      chatMessages.value.push({ role: 'user', text: msgText });
      chatInput.value = '';
      chatLoading.value = true;
      scrollToBottom();

      const history = chatMessages.value.slice(0, -1).map(item => ({
        role: item.role === 'ai' ? 'model' : item.role,
        text: item.text
      }));

      try {
        const res = await api(getChatEndpointPath(), {
          method: 'POST',
          body: JSON.stringify({
            message: msgText,
            history
          })
        });

        if (res && res.response) {
          chatMessages.value.push({ role: 'ai', text: res.response });
        } else {
          chatMessages.value.push({ role: 'ai', text: 'Desculpe, não consegui obter uma resposta válida da inteligência artificial.' });
        }
      } catch (err) {
        console.error('Erro no chat da IA:', err);
        const backendMessage = err.fieldErrors?.response || err.rawText || err.message || 'Erro desconhecido';
        chatMessages.value.push({
          role: 'ai',
          text: `Desculpe, ocorreu um erro ao conectar com o serviço da IA. ${backendMessage}`
        });
      } finally {
        chatLoading.value = false;
        scrollToBottom();
      }
    }

    function sendSuggestion(type) {
      let promptText = '';

      // Técnico
      if (type === 'Como Consertar') {
        promptText = 'Analise as detecções críticas recentes e suas leituras. Quais verificações e atendimentos nas O.S. vinculadas são recomendados?';
      } else if (type === 'O Que Fazer') {
        promptText = 'O que devo fazer com as ordens de serviço pendentes e como priorizá-las em campo?';
      } else if (type === 'Sugerir Preventivas') {
        promptText = 'Com base nos sensores de telemetria e ordens abertas, quais manutenções preventivas você sugere realizar?';
      }
      // Gestor
      else if (type === 'Status Empresa') {
        promptText = 'Qual é o status geral de funcionamento dos equipamentos e o resumo de custos da minha empresa?';
      } else if (type === 'Gestão de Equipe') {
        promptText = 'Quais são as melhores ferramentas ou práticas para otimizar a alocação da minha equipe de manutenção?';
      } else if (type === 'Redução de Custos') {
        promptText = 'Com base no histórico e nos KPIs, onde há maior oportunidade para reduzir custos de manutenção?';
      }
      // Admin
      else if (type === 'Visão Global') {
        promptText = 'Qual o desempenho comparativo, MTBF e MTTR médio de todas as empresas e ativos cadastrados?';
      } else if (type === 'Estratégia Sistêmica') {
        promptText = 'Quais ferramentas de alta gestão e estratégias sistêmicas você sugere para melhorar a confiabilidade de toda a plataforma?';
      } else if (type === 'Alertas Críticos Globais') {
        promptText = 'Analise as ocorrências críticas recentes, a condição atual dos sensores e suas O.S. Quais atendimentos exigem escalonamento?';
      }

      if (promptText) {
        chatInput.value = promptText;
        nextTick(() => {
          resizeChatInput();
          if (chatInputField.value) {
            chatInputField.value.focus();
          }
        });
      }
    }

    function formatMarkdown(text) {
      if (!text) return '';
      const escapeHtml = (value) => String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
      let lines = text.split('\n');
      let insideList = false;
      let result = [];

      for (let line of lines) {
        let trimmed = escapeHtml(line.trim());
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          if (!insideList) {
            result.push('<ul>');
            insideList = true;
          }
          let liContent = trimmed.substring(2);
          liContent = liContent.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
          result.push(`<li>${liContent}</li>`);
        } else {
          if (insideList) {
            result.push('</ul>');
            insideList = false;
          }
          let formattedLine = trimmed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
          if (formattedLine === '') {
            result.push('<br>');
          } else {
            result.push(`<p>${formattedLine}</p>`);
          }
        }
      }
      if (insideList) {
        result.push('</ul>');
      }
      return result.join('');
    }

    async function uploadFotoPerfil(event) {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append('foto_perfil', file);

      try {
        const res = await fetch(`${BASE}/api/auth/me/`, {
          method: 'PATCH',
          headers: { 'Authorization': `Bearer ${token.value}` },
          body: formData
        });
        if (!res.ok) throw new Error('Falha ao enviar foto');
        const data = await res.json();
        me.value = data;
        
        // Atualiza na lista de usuários também, se estiver carregada
        const uIndex = lists.usuarios.findIndex(u => u.id === data.id);
        if (uIndex !== -1) {
          lists.usuarios[uIndex] = { ...lists.usuarios[uIndex], foto_perfil: data.foto_perfil };
        }
        
        toasts.value.push({ msg: 'Foto de perfil atualizada!', type: 'success' });
        setTimeout(() => toasts.value.shift(), 3000);
      } catch (err) {
        console.error(err);
        toasts.value.push({ msg: 'Erro ao enviar foto.', type: 'error' });
        setTimeout(() => toasts.value.shift(), 3000);
      }
    }

    return {
      orderAnalysis, analyzeOrder, osPrompt, promptCompanyId, saveOsPrompt, loadOtherPrompts,
      orderDetail, openOrderDetails, closeOrderDetails, orderDetailKeydown, orderStatusLabel, orderTypeLabel, orderExtraFilters,
      alertLevelLabel, orderEscalations, orderLastEscalation, fmtTimestamp,
      orderState, orderParams, selectOrderPriority, clearOrderFilters, equipmentGuide, equipmentAssessment, criteriaModal,
      loadEquipmentGuide, acceptEquipmentSuggestion, openCriteria, loadCriteria, saveCriteria, criticidadeLabel, historicPriorityLabel, priorityOrigin,
      priorityModal, openPriority, savePriority, orderEquipmentOptions,
      api, dashboardCostChart, dashboardSummary, dashboardCards, dashboardCompanies, dashboardOrders, dashboardAdminOverview,
      companySearch, dashboardTab, performanceOpen, liveOpen, telemetryLiveOpen, dashboardUpdatedAt,
      dashboardCompany, applyDashboardFilters, togglePerformance, dashboardAction, dashboardAllAlerts, openDashboardOrders, openDashboardOrder, metric,
      token, me, view, loading, loginLoading, loginError, loginForm,
      kpis, dashAlerts, alertCount, toasts, lists, pages, filters,
      modal, fd, formErrors, globalEmpresa,
      alertHistory, alertSensors, alertEvidence, alertReadings, alertThresholds, alertChart, enterAlertHistory,
      openAlertaDetails, closeAlertaDetails, openAlertaOS, openAlertaSensor, showEquipmentAlerts,
      isAdmin, isAdminOrGestor, isTecnico, userInitial, viewTitle, osSemTecnicoCount,
      doLogin, logout, navigate, debouncedFetch,
      telemetry, telemetrySensors, telemetryCount, telemetryRows, trendSummary, trendChart, trendPage, trendCount, trendRows, trendEquipments, trendSensors,
      selectedTrend, selectedTrendChart, buildTrendChart, setTrendTimePreset,
      trendEquipmentOptions, selectTrendEquipment, trendMinutes, trendInterventionLabel, trendPersistencePercent, trendR2Percent,
      scopedTrendCount,
      closeTrendConfig, trendConfigKeydown,
      trendDemo, runTrendDemo, toggleTrendTestMode,
      fetchTrends, applyTrendFilters, clearTrendFilters, changeTrendPage, openTrendDetail, showTrends,
      sensorTipoLabel, trendCondition, trendConditionLabel, trendDirection, setTelemetryTab, applyTelemetryFilters,
      clearTelemetryFilters, changeTelemetryPage, enterTelemetry,
      fetchEquipamentos, fetchAlertas, fetchOrdens, fetchTelemetria,
      fetchHistorico, fetchEmpresas, fetchUsuarios, fetchLocalizacoes, fetchPrompts, fetchPage, fetchDashboard,
      openModal, editItem, saveItem, deleteItem, exportData, assumirOS, iniciarAtendimento, openEncerrarOS,
      formatNumber, fmtDate, nivelBadge, nivelColor, statusBadge, eqStatusBadge,
      ordemStatusBadge, prioridadeBadge, prioridadeIcon, prioridadeLabel,
      eqNome, getEquipamentoInfo, osTitulo, osEquipNome, eqEmpresaNome, empresaNome, sensorNome, locSetor, custoTotal, countSensores, usuarioNome,
      empresaNomeSensor, sensorEquipNome,
      onGlobalEmpresaChange,
      chartEquipStatus, chartAlertNivel, chartOrdens, chartCustoEvolucao,
      dashboardEquipamentos,
      dashAlertsCollapsed, dashOrdensCollapsed, ordensFilaPrioridade,
      donutArcs,
      availableSectors,
      leiturasTodayCount, leiturasTotalCount, dashTelemetriaEquip, dashTelemetriaSensor,
      dashCustoSetor,
      dashSetor, dashEquipamento, explainerCollapsed, dashboardMetrics, dashboardEquipmentOptions, availableDashboardSectors, dashboardKpisLoading, dashboardKpisError,
      trendMonitor, refreshTrendMonitoring, reviewNewTrends, startTrendPolling,
      trendAlerts, trendDataCache, trendAILoading, trendConfigModal,
      analyzeSensorTrendAI, openTrendConfig, saveTrendConfig,
      equipModal, selectedSensorLabel, selectedSensorThresholds, sensorModalThresholds, equipModalChart, equipModalStats, equipModalFilteredOrdens,
      openEquipamentoDetails, closeEquipModal, fetchEquipamentoReadings,
      savePrompt, resetPrompt,
      chatOpen, chatExpanded, chatAtBottom, chatInput, chatLoading, chatMessages, chatScrollContainer,
      chatInputField, chatPlaceholder,
      darkMode, toggleTheme,
      toggleChat, toggleChatExpand, handleChatKeydown, resizeChatInput, sendChatMessage, sendSuggestion, onChatScroll, scrollToBottom, formatMarkdown,
      testerMode, toggleTesterMode,
      navigateMinhasOrdens, navigateOsSemTecnico,
      uploadFotoPerfil
    };
  }
}).mount('#app');
