const { createApp, ref, reactive, computed, onMounted, watch, nextTick } = Vue;
const BASE = 'http://127.0.0.1:9000';
const TELEMETRY_CHART_WIDTH = 320;
const TELEMETRY_CHART_HEIGHT = 100;
const TELEMETRY_CHART_LEFT_PAD = 45;
const TELEMETRY_X_END_PERCENT = 0.7; // last point reaches about 70% of chart width

// Helper: ordena por nível de severidade (critica → alta → media → baixa)
const NIVEL_PRIORIDADE = { critica: 0, alta: 1, media: 2, baixa: 3 };
function sortByNivel(items, campo = 'nivel') {
  return items.sort((a, b) => (NIVEL_PRIORIDADE[a[campo]] ?? 3) - (NIVEL_PRIORIDADE[b[campo]] ?? 3));
}

// Helper: ordena por tipo de usuário (admin → gestor → tecnico)
const TIPO_USUARIO_PRIORIDADE = { admin: 0, gestor: 1, tecnico: 2 };
function sortByTipoUsuario(items, campo = 'tipo_usuario') {
  return items.sort((a, b) => (TIPO_USUARIO_PRIORIDADE[a[campo]] ?? 3) - (TIPO_USUARIO_PRIORIDADE[b[campo]] ?? 3));
}

createApp({
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
    const filtroFilaPrioridade = ref('todas');
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

    const lists = reactive({
      equipamentos: [], alertas: [], ordens: [],
      sensores: [], leituras: [], historico: [], empresas: [],
      usuarios: [], localizacoes: [], prompts: []
    });
    const trendAlerts = ref([]); // Painel de tendências de risco
    const trendDataCache = reactive({}); // sensor_id -> dados de tendência + ai_analysis
    const trendAILoading = reactive({}); // sensor_id -> booleano
    const trendConfigModal = reactive({
      open: false, loading: false, saving: false,
      sensorId: '', equipamentoId: '',
      form: { periodo_horas: 24, num_leituras: 50, sensibilidade: 'media' },
      isGlobal: false
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
      alertas: { search: '', nivel: '', status: '' },
      ordens: { search: '', status: '', prioridade: '', tipo_os: '' },
      telemetria_sensores: { search: '', tipo: '', ativo: '' },
      telemetria_leituras: { valor_min: '', valor_max: '', timestamp_de: '', timestamp_ate: '' },
      historico: { search: '', data_de: '', data_ate: '', custo_min: '', custo_max: '' },
      empresas: { search: '' },
      usuarios: { search: '' },
      localizacoes: { search: '', setor: '' },
    });

    // ─ Modal ─────────────────────────────────────────
    const modal = reactive({ open: false, type: '', title: '', editId: null, saving: false, oldStatus: null });
    const fd = reactive({});
    const formErrors = ref({});

    const equipModal = reactive({
      open: false,
      equipamento: null,
      currentOS: null,
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
      if (equipModal.osFilter === 'alertas') return equipModal.ordens.filter(o => o.titulo.toLowerCase().includes('alerta'));
      if (equipModal.osFilter === 'os') return equipModal.ordens.filter(o => !o.titulo.toLowerCase().includes('alerta'));
      return equipModal.ordens;
    });

    // ─ Computed básicos ──────────────────────────────
    const isAdmin = computed(() => me.value?.tipo_usuario === 'admin');
    const isAdminOrGestor = computed(() => ['admin', 'gestor'].includes(me.value?.tipo_usuario));
    const isTecnico = computed(() => me.value?.tipo_usuario === 'tecnico');
    const osSemTecnicoCount = computed(() => lists.ordens.filter(o => !o.responsavel && o.status !== 'concluida' && o.status !== 'cancelada').length);
    
    const ordensFilaPrioridade = computed(() => {
      let pendentes = lists.ordens.filter(o => o.status !== 'concluida' && o.status !== 'cancelada');
      if (filtroFilaPrioridade.value !== 'todas') {
        pendentes = pendentes.filter(o => o.prioridade === filtroFilaPrioridade.value);
      }
      return pendentes.sort((a, b) => {
        const pa = NIVEL_PRIORIDADE[a.prioridade] ?? 99;
        const pb = NIVEL_PRIORIDADE[b.prioridade] ?? 99;
        return pa - pb;
      });
    });

    const userInitial = computed(() => (me.value?.username || 'U')[0].toUpperCase());
    const viewTitle = computed(() => ({
      dashboard: 'Dashboard', equipamentos: 'Equipamentos', alertas: 'Alertas',
      ordens: 'Ordens de Serviço', telemetria: 'Telemetria',
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
      const counts = dashboardSummary.value?.alertas_ativos
        ? { ...dashboardSummary.value.alertas_ativos }
        : { critico: 0, medio: 0, baixo: 0 };
      if (!dashboardSummary.value) {
        dashAlerts.value.forEach(a => { if (counts[a.nivel] !== undefined) counts[a.nivel]++; });
      }
      const max = Math.max(...Object.values(counts), 1);
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

    const dashboardEquipamentos = computed(() => {
      if (!isTecnico.value) return lists.equipamentos;
      const allowedIds = new Set(lists.ordens.map(o => o.equipamento).filter(Boolean));
      return lists.equipamentos.filter(eq => allowedIds.has(eq.id));
    });

    const dashboardAllowedEquipamentoIds = computed(() => new Set(dashboardEquipamentos.value.map(eq => eq.id)));

    const availableDashboardSectors = computed(() => {
      return [...new Set(dashboardEquipamentos.value.map(eq => locSetor(eq.id)).filter(Boolean))].sort();
    });

    const dashboardEquipmentOptions = computed(() => {
      if (!dashSetor.value) return dashboardEquipamentos.value;
      return dashboardEquipamentos.value.filter(eq => locSetor(eq.id) === dashSetor.value);
    });

    const dashboardKpisFiltered = computed(() => {
      const allowedIds = new Set(dashboardEquipamentos.value.map(eq => eq.id));
      return dashboardKpis.value
        .filter(k => allowedIds.has(k.equipamento_id))
        .filter(k => !dashSetor.value || locSetor(k.equipamento_id) === dashSetor.value)
        .filter(k => !dashEquipamento.value || k.equipamento_id === Number(dashEquipamento.value));
    });

    const dashboardMetrics = computed(() => {
      const global = dashboardSummary.value?.kpis_globais;
      if (global) {
        return {
          mttr: Number(global.mttr_medio || 0).toFixed(2),
          mtbf: Number(global.mtbf_medio || 0).toFixed(2),
          disponibilidade: Number(global.disponibilidade_media || 0).toFixed(2),
          custo: Number(global.custo_total_manutencao || 0).toFixed(2),
          total: dashboardSummary.value.detalhes_equipamentos?.length || 0,
        };
      }
      const items = dashboardKpisFiltered.value;
      if (!items.length) {
        return { mttr: '—', mtbf: '—', disponibilidade: '—', custo: '—', total: 0 };
      }
      const validMttr = items.filter(k => k.total_manutencoes > 0).map(k => Number(k.mttr_hours) || 0);
      const validMtbf = items.filter(k => k.mtbf_hours > 0).map(k => Number(k.mtbf_hours) || 0);
      const validDisp = items.map(k => k.disponibilidade_porcentagem).filter(v => v !== null && v !== undefined);
      const avg = (arr) => arr.length ? (arr.reduce((sum, value) => sum + value, 0) / arr.length).toFixed(2) : '—';
      return {
        mttr: avg(validMttr),
        mtbf: avg(validMtbf),
        disponibilidade: avg(validDisp),
        custo: items.reduce((sum, k) => sum + (Number(k.custo_total_manutencao) || 0), 0).toFixed(2),
        total: items.length,
      };
    });

    watch(dashSetor, () => {
      if (dashEquipamento.value && !dashboardEquipmentOptions.value.some(eq => eq.id === Number(dashEquipamento.value))) {
        dashEquipamento.value = '';
      }
    });

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

    const dashboardSensors = computed(() => {
      if (!isTecnico.value) return lists.sensores;
      const allowedEqIds = dashboardAllowedEquipamentoIds.value;
      return lists.sensores.filter(s => allowedEqIds.has(getEquipamentoId(s.equipamento)));
    });

    // ─ Leituras Hoje vs Total ─────────────────────────
    const leiturasHoje = computed(() => {
      const hoje = new Date();
      const hojeStr = hoje.toISOString().slice(0, 10); // 'YYYY-MM-DD'
      return lists.leituras.filter(l => {
        if (!l.timestamp) return false;
        return l.timestamp.slice(0, 10) === hojeStr;
      });
    });

    // ─ Sensores filtrados pelo equipamento selecionado ─
    const dashTelemetriaSensoresFiltrados = computed(() => {
      const source = isTecnico.value ? dashboardSensors.value : lists.sensores;
      if (!dashTelemetriaEquip.value) return source;
      const eqId = Number(dashTelemetriaEquip.value);
      return source.filter(s => getEquipamentoId(s.equipamento) === eqId);
    });

    watch(dashboardEquipamentos, (equipamentos) => {
      if (equipamentos.length && !dashTelemetriaEquip.value) {
        dashTelemetriaEquip.value = equipamentos[0].id;
      }
    });

    watch(dashTelemetriaEquip, (eq) => {
      const filteredSensors = dashTelemetriaSensoresFiltrados.value;
      if (filteredSensors.length) {
        if (!dashTelemetriaSensor.value || !filteredSensors.some(s => s.id === Number(dashTelemetriaSensor.value))) {
          dashTelemetriaSensor.value = filteredSensors[0].id;
        }
      } else {
        dashTelemetriaSensor.value = '';
      }
    });

    watch(dashTelemetriaSensoresFiltrados, (sensors) => {
      if (sensors.length && !dashTelemetriaSensor.value) {
        dashTelemetriaSensor.value = sensors[0].id;
      }
    });

    function formatChartTimestamp(ts) {
      if (!ts) return '';
      return ts.slice(11, 16);
    }

    const chartTelemetria = computed(() => {
      let leiturasSource = lists.leituras;

      // Se nenhum sensor específico for selecionado na UI, precisamos pegar apenas 
      // as leituras de UM único sensor para o gráfico formar uma linha do tempo real.
      let targetSensorId = dashTelemetriaSensor.value ? Number(dashTelemetriaSensor.value) : null;

      if (!targetSensorId && leiturasSource.length > 0) {
        // Pega o sensor da leitura mais recente da lista filtrada pelo equipamento (ou global)
        if (dashTelemetriaEquip.value) {
          const eqId = Number(dashTelemetriaEquip.value);
          const sensorIds = new Set(lists.sensores.filter(s => getEquipamentoId(s.equipamento) === eqId).map(s => s.id));
          const firstValid = leiturasSource.find(l => sensorIds.has(l.sensor));
          if (firstValid) targetSensorId = firstValid.sensor;
        } else {
          targetSensorId = leiturasSource[0].sensor;
        }
      }

      if (targetSensorId) {
        leiturasSource = leiturasSource.filter(l => l.sensor === targetSensorId);
      }

      // API retorna ordenado por -timestamp (mais recente primeiro); revertemos para exibir cronologicamente no gráfico
      const raw = leiturasSource.slice(0, 20).reverse();
      if (raw.length < 2) return { path: '', dots: [], min: 0, max: 0, count: raw.length, xLabels: [], yTicks: [] };
      const sensorMap = new Map(lists.sensores.map(s => [s.id, s]));
      const vals = raw.map(l => parseFloat(l.valor) || 0);
      const thresholdSensor = dashTelemetriaSensor.value ? sensorMap.get(Number(dashTelemetriaSensor.value)) : null;
      const thresholdValues = thresholdSensor && thresholdSensor.limite_alerta ? [
        Number((thresholdSensor.limite_alerta_baixo_pct || 70) * thresholdSensor.limite_alerta / 100),
        Number((thresholdSensor.limite_alerta_medio_pct || 85) * thresholdSensor.limite_alerta / 100),
        Number((thresholdSensor.limite_alerta_critico_pct || 100) * thresholdSensor.limite_alerta / 100),
      ] : [];
      const extendedVals = vals.concat(thresholdValues.filter(v => Number.isFinite(v)));
      const rawMin = Math.min(...extendedVals);
      const rawMax = Math.max(...extendedVals);
      const min = telemetryYAxis.min === null ? rawMin : Math.min(telemetryYAxis.min, rawMin);
      const max = telemetryYAxis.max === null ? rawMax : Math.max(telemetryYAxis.max, rawMax);
      const chartRange = Math.max(max - min, 1);

      if (telemetryYAxis.min === null || rawMin < telemetryYAxis.min) {
        telemetryYAxis.min = rawMin;
      }
      if (telemetryYAxis.max === null || rawMax > telemetryYAxis.max) {
        telemetryYAxis.max = rawMax;
      }
      const W = TELEMETRY_CHART_WIDTH;
      const H = TELEMETRY_CHART_HEIGHT;
      const padding = 16;
      const leftPad = TELEMETRY_CHART_LEFT_PAD;
      const chartW = W - leftPad;
      const visibleChartW = chartW * TELEMETRY_X_END_PERCENT;
      const points = raw.map((l, i) => {
        const v = parseFloat(l.valor) || 0;
        const sensor = sensorMap.get(l.sensor) || {};
        return {
          x: leftPad + (i / (raw.length - 1)) * visibleChartW,
          y: padding + (1 - ((v - min) / chartRange)) * (H - padding * 2),
          v,
          timestamp: l.timestamp,
          label: sensor.nome || `Sensor ${l.sensor}`,
          unit: sensor.unidade_medida || '',
          sensorId: l.sensor,
        };
      });
      const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
      const area = path + ` L${W},${H} L${leftPad},${H} Z`;
      const yTicks = Array.from({ length: 4 }, (_, idx) => {
        const value = min + ((chartRange) * idx / 3);
        return { y: padding + (1 - ((value - min) / chartRange)) * (H - padding * 2), label: value.toFixed(1) };
      });
      const xLabels = [
        { x: leftPad, label: formatChartTimestamp(raw[0].timestamp) },
        { x: leftPad + visibleChartW / 2, label: formatChartTimestamp(raw[Math.floor(raw.length / 2)].timestamp) },
        { x: leftPad + visibleChartW, label: formatChartTimestamp(raw[raw.length - 1].timestamp) },
      ];

      const selectedSensor = dashTelemetriaSensor.value
        ? sensorMap.get(Number(dashTelemetriaSensor.value))
        : null;
      const thresholds = [];
      if (selectedSensor && selectedSensor.limite_alerta) {
        const t = computeSensorThresholds(selectedSensor);
        const rawThresholds = [
          { name: 'Baixo', display: t.lowValue, value: Number(t.lowValue), pct: t.lowPct, color: 'var(--warn)', dash: '4 4' },
          { name: 'Médio', display: t.medValue, value: Number(t.medValue), pct: t.medPct, color: 'var(--acid)', dash: '4 4' },
          { name: 'Crítico', display: t.critValue, value: Number(t.critValue), pct: t.critPct, color: 'var(--danger)', dash: '4 4' },
        ].filter(th => Number.isFinite(th.value));

        thresholds.push(...rawThresholds.map(th => ({
          ...th,
          unit: t.unit,
          y: padding + (1 - ((th.value - min) / chartRange)) * (H - padding * 2),
        })));
      }

      return {
        path,
        area,
        dots: points,
        min: min.toFixed(1),
        max: max.toFixed(1),
        count: leiturasSource.length,
        yTicks,
        xLabels,
        thresholds,
        leftPad,
        chartW,
        visibleChartW,
      };
    });

    const telemetryYAxis = reactive({ min: null, max: null });
    const displayedChartTelemetria = ref(chartTelemetria.value);
    const testerMode = ref(false);
    const telemetrySlideOffset = ref(0);
    const telemetryMovingDot = reactive({ x: 0, y: 0, visible: false });
    let telemetryAnimationFrame = null;

    function toggleTesterMode() {
      testerMode.value = !testerMode.value;
    }

    function lerp(a, b, t) {
      return a + (b - a) * t;
    }

    function easeOutQuad(t) {
      return t * (2 - t);
    }

    function buildChartFromDots(dots, baseChart) {
      const path = dots.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
      const lastPoint = dots[dots.length - 1];
      return {
        ...baseChart,
        dots,
        path,
        area: path + ` L${lastPoint.x.toFixed(1)},100 L${baseChart.leftPad},100 Z`,
      };
    }

    function updateDisplayedChartWithDots(dots, baseChart) {
      if (!dots.length) return;
      displayedChartTelemetria.value = buildChartFromDots(dots, baseChart);
    }

    function isSameTelemetrySource(currentChart, nextChart) {
      if (!currentChart?.dots?.length || !nextChart?.dots?.length) return false;
      const currentSensor = currentChart.dots[currentChart.dots.length - 1]?.sensorId;
      const nextSensor = nextChart.dots[nextChart.dots.length - 1]?.sensorId;
      return currentSensor !== undefined && currentSensor === nextSensor;
    }

    function animateChartTransition(nextChart) {
      const currentChart = displayedChartTelemetria.value;
      if (!currentChart || !currentChart.dots?.length || !nextChart?.dots?.length || currentChart.dots.length !== nextChart.dots.length) {
        if (telemetryAnimationFrame) cancelAnimationFrame(telemetryAnimationFrame);
        telemetrySlideOffset.value = 0;
        telemetryMovingDot.visible = false;
        displayedChartTelemetria.value = nextChart;
        return;
      }

      if (!isSameTelemetrySource(currentChart, nextChart)) {
        if (telemetryAnimationFrame) cancelAnimationFrame(telemetryAnimationFrame);
        telemetrySlideOffset.value = 0;
        telemetryMovingDot.visible = false;
        displayedChartTelemetria.value = nextChart;
        return;
      }

      const stepX = currentChart.dots[1].x - currentChart.dots[0].x;
      const lastCurrentPoint = currentChart.dots[currentChart.dots.length - 1];
      const nextLastPoint = nextChart.dots[nextChart.dots.length - 1];
      const newPoint = { ...nextLastPoint, x: lastCurrentPoint.x + stepX };
      if (newPoint.timestamp === lastCurrentPoint.timestamp) {
        return;
      }

      const slideDots = [...currentChart.dots, newPoint];
      displayedChartTelemetria.value = buildChartFromDots(slideDots, currentChart);
      telemetrySlideOffset.value = 0;
      telemetryMovingDot.visible = false;
      if (telemetryAnimationFrame) cancelAnimationFrame(telemetryAnimationFrame);

      const start = performance.now();
      const duration = 2600;

      function animate(now) {
        const rawProgress = Math.min(Math.max((now - start) / duration, 0), 1);
        const progress = easeOutQuad(rawProgress);
        telemetrySlideOffset.value = lerp(0, -stepX, progress);

        if (rawProgress < 1) {
          telemetryAnimationFrame = requestAnimationFrame(animate);
        } else {
          telemetrySlideOffset.value = 0;
          const finalDots = currentChart.dots.slice(1).map(dot => ({ ...dot, x: dot.x - stepX }));
          const finalChart = buildChartFromDots([...finalDots, { ...newPoint, x: lastCurrentPoint.x }], currentChart);
          displayedChartTelemetria.value = finalChart;
        }
      }

      telemetryAnimationFrame = requestAnimationFrame(animate);
    }

    watch(chartTelemetria, (next, prev) => {
      const nextDots = next?.dots || [];
      if (nextDots.length < 2) {
        displayedChartTelemetria.value = next;
        telemetryMovingDot.visible = false;
        telemetryYAxis.min = null;
        telemetryYAxis.max = null;
        return;
      }
      if (!displayedChartTelemetria.value?.dots?.length || next.dots.length !== displayedChartTelemetria.value.dots.length) {
        displayedChartTelemetria.value = next;
        return;
      }
      animateChartTransition(next);
    });

    const telemetriaSummary = computed(() => {
      if (!lists.leituras.length) {
        return {
          min: '—', max: '—', avg: '—', latest: '—', latest_sensor: '—', latest_equip: '—', limit: '—', criticos: 0, acima_alerta: 0, thresholds: null
        };
      }

      const sensorMap = new Map(lists.sensores.map(s => [s.id, s]));
      const values = lists.leituras.map(l => parseFloat(l.valor) || 0);
      const avg = (values.reduce((sum, v) => sum + v, 0) / values.length).toFixed(2);
      const min = Math.min(...values).toFixed(2);
      const max = Math.max(...values).toFixed(2);
      const latest = lists.leituras[0];
      const selectedSensor = dashTelemetriaSensor.value ? sensorMap.get(Number(dashTelemetriaSensor.value)) : null;
      const activeSensor = selectedSensor || sensorMap.get(latest.sensor);
      const latestSensor = sensorMap.get(latest.sensor) || {};
      const limit = activeSensor?.limite_alerta || latestSensor.limite_alerta || 0;
      const latestEquip = lists.equipamentos.find(eq => eq.id === (selectedSensor?.equipamento || latestSensor.equipamento)) || {};
      const thresholds = computeSensorThresholds(activeSensor);
      const openOrders = lists.ordens.filter(o => {
        if (!o.equipamento) return false;
        const eId = typeof o.equipamento === 'object' ? o.equipamento.id : o.equipamento;
        return eId === latestEquip.id && o.status !== 'concluida' && o.status !== 'cancelada';
      }).length;
      const criticos = lists.leituras.filter(l => {
        const sensor = sensorMap.get(l.sensor);
        if (!sensor || !sensor.limite_alerta) return false;
        return parseFloat(l.valor) >= sensor.limite_alerta * 0.9;
      }).length;
      const acima_alerta = lists.leituras.filter(l => {
        const sensor = sensorMap.get(l.sensor);
        if (!sensor || !sensor.limite_alerta) return false;
        return parseFloat(l.valor) >= sensor.limite_alerta * 0.7;
      }).length;

      return {
        min,
        max,
        avg,
        latest: parseFloat(latest.valor).toFixed(2),
        latest_sensor: activeSensor?.nome || latestSensor.nome || 'Sensor',
        latest_equip: latestEquip.nome || 'Equipamento',
        unit: activeSensor?.unidade_medida || latestSensor.unidade_medida || '',
        limit: limit ? limit.toFixed(2) : '—',
        criticos,
        acima_alerta,
        open_orders: openOrders,
        lowPct: thresholds?.lowPct,
        medPct: thresholds?.medPct,
        critPct: thresholds?.critPct,
        lowValue: thresholds?.lowValue,
        medValue: thresholds?.medValue,
        critValue: thresholds?.critValue,
        thresholds,
      };
    });

    watch([dashTelemetriaEquip, dashTelemetriaSensor], async ([eq, sen]) => {
      let url = '/api/telemetria/leituras/?limit=200&ordering=-timestamp';
      if (sen) {
        url += '&sensor=' + sen;
      }

      try {
        const res = await api(url);
        if (res) {
          let readings = normList(res);
          if (eq && !sen) {
            const sensorIds = new Set(lists.sensores.filter(s => s.equipamento === Number(eq)).map(s => s.id));
            readings = readings.filter(l => sensorIds.has(l.sensor));
          }
          if (globalEmpresa.value) {
            const filterIds = new Set(lists.sensores.map(s => s.id));
            readings = readings.filter(l => filterIds.has(l.sensor));
          }
          lists.leituras = readings;
        }
      } catch (err) {
        console.error("Erro ao buscar leituras filtradas no dashboard", err);
      }
    });

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
        navigate('dashboard');
      } catch (e) { loginError.value = e.message; }
      finally { loginLoading.value = false; }
    }

    async function fetchMe() {
      try { me.value = await api('/api/auth/me/'); } catch { }
    }

    function logout() {
      token.value = ''; refreshTk.value = ''; me.value = null;
      localStorage.removeItem('sentinel_token');
      localStorage.removeItem('sentinel_refresh');
    }

    // ─ Navigation ────────────────────────────────────
    const fetchers = {
      dashboard: () => fetchDashboard(),
      equipamentos: () => fetchEquipamentos(),
      alertas: () => fetchAlertas(),
      ordens: () => fetchOrdens(),
      telemetria: () => fetchTelemetria(),
      historico: () => fetchHistorico(),
      empresas: () => fetchEmpresas(),
      usuarios: () => fetchUsuarios(),
      localizacoes: () => fetchLocalizacoes(),
      prompts: () => fetchPrompts(),
    };
    function navigate(v) { view.value = v; fetchers[v]?.(); }

    // Navegação dos cards clicáveis do técnico no dashboard
    function navigateMinhasOrdens() {
      filters.ordens.status = '';
      filters.ordens.prioridade = '';
      filters.ordens.tipo_os = '';
      navigate('ordens');
      // Após carregar, filtra client-side para mostrar apenas as atribuídas ao técnico
      nextTick(() => {
        const userId = me.value?.id;
        if (userId) {
          lists.ordens = lists.ordens.filter(o => o.responsavel === userId && o.status !== 'concluida' && o.status !== 'cancelada');
        }
      });
    }

    function navigateOsSemTecnico() {
      filters.ordens.status = '';
      filters.ordens.prioridade = '';
      filters.ordens.tipo_os = '';
      navigate('ordens');
      // Após carregar, filtra client-side para mostrar apenas O.S. sem responsável
      nextTick(() => {
        lists.ordens = lists.ordens.filter(o => !o.responsavel && o.status !== 'concluida' && o.status !== 'cancelada');
      });
    }

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

    async function fetchDashboardKpis() {
      dashboardKpisLoading.value = true;
      dashboardKpisError.value = null;
      try {
        const query = globalEmpresa.value ? `?empresa_id=${encodeURIComponent(globalEmpresa.value)}` : '';
        const data = await api('/api/dashboards/resumo/' + query);
        dashboardSummary.value = data;
        dashboardKpis.value = data?.detalhes_equipamentos || [];
      } catch (err) {
        dashboardKpisError.value = err?.message || 'Falha ao carregar KPIs';
        toast(dashboardKpisError.value, 'error');
        dashboardKpis.value = [];
        dashboardSummary.value = null;
      } finally {
        dashboardKpisLoading.value = false;
      }
    }

    async function fetchDashboard() {
      try {
        const empParam = globalEmpresa.value ? '&empresa=' + globalEmpresa.value : '';
        const [eqRes, alertRes, ordRes, histRes] = await Promise.allSettled([
          api('/api/equipamentos/?limit=200' + empParam),
          api('/api/alertas/?status=ativo&limit=100&ordering=-criado_em' + (globalEmpresa.value ? '&equipamento__empresa=' + globalEmpresa.value : '')),
          api('/api/ordens-servico/?limit=100' + (globalEmpresa.value ? '&equipamento__empresa=' + globalEmpresa.value : '')),
          api('/api/historico/?limit=50' + (globalEmpresa.value ? '&ordem_servico__equipamento__empresa=' + globalEmpresa.value : '')),
        ]);

        if (eqRes.status === 'fulfilled' && eqRes.value) lists.equipamentos = normList(eqRes.value);
        if (ordRes.status === 'fulfilled' && ordRes.value) lists.ordens = normList(ordRes.value);
        if (histRes.status === 'fulfilled' && histRes.value) lists.historico = normList(histRes.value);

        const eqIds = globalEmpresa.value
          ? new Set(lists.equipamentos.map(eq => eq.id))
          : null;

        if (eqIds) {
          lists.ordens = lists.ordens.filter(o => eqIds.has(o.equipamento));
        }

        const allowedEqIds = isTecnico.value
          ? new Set(lists.ordens.map(o => o.equipamento).filter(Boolean))
          : eqIds;

        if (isTecnico.value && allowedEqIds && allowedEqIds.size) {
          lists.equipamentos = lists.equipamentos.filter(eq => allowedEqIds.has(eq.id));
        }

        if (alertRes.status === 'fulfilled' && alertRes.value) {
          let alerts = normList(alertRes.value);
          if (allowedEqIds) {
            alerts = alerts.filter(a => allowedEqIds.has(a.equipamento));
          }
          sortByNivel(alerts);
          dashAlerts.value = alerts;
          alertCount.value = alerts.length;
        }

        const sensorFilter = allowedEqIds && allowedEqIds.size
          ? '&equipamento__in=' + [...allowedEqIds].join(',')
          : '';
        const sensorRes = await api('/api/telemetria/sensores/?limit=999' + sensorFilter);
        if (sensorRes) lists.sensores = normList(sensorRes);

        const today = new Date().toISOString().slice(0, 10);
        const timestampDe = `${today}T00:00:00`;
        const timestampAte = `${today}T23:59:59`;

        const telUrl = buildTelemetriaUrl({
          limit: 50,
          allowedEqIds: dashboardAllowedEquipamentoIds.value,
          sensorId: dashTelemetriaSensor.value,
          equipamentoId: dashTelemetriaEquip.value,
        });
        const telRes = await api(telUrl);
        const telHojeRes = await api(buildTelemetriaUrl({
          limit: 1,
          allowedEqIds: dashboardAllowedEquipamentoIds.value,
          timestampDe,
          timestampAte,
        }));
        const telTotalRes = await api(buildTelemetriaUrl({
          limit: 1,
          allowedEqIds: dashboardAllowedEquipamentoIds.value,
        }));

        if (telRes) {
          let leituras = normList(telRes);
          if (lists.sensores.length) {
            const sensorIds = new Set(lists.sensores.map(s => s.id));
            leituras = leituras.filter(l => sensorIds.has(l.sensor));
          }
          lists.leituras = leituras;
        }
        if (telTotalRes) {
          leiturasTotalCount.value = Number(telTotalRes.count ?? 0) || 0;
        } else {
          leiturasTotalCount.value = 0;
        }
        if (telHojeRes) {
          leiturasTodayCount.value = Number(telHojeRes.count ?? 0) || 0;
        } else {
          leiturasTodayCount.value = 0;
        }

        if (histRes.status === 'fulfilled' && histRes.value) lists.historico = normList(histRes.value);

        if (!isTecnico.value) {
          await fetchDashboardKpis();
        } else {
          dashboardKpis.value = [];
        }

        if (isTecnico.value) {
          const ordensAbertas = lists.ordens.filter(o => o.status === 'pendente' || o.status === 'andamento');
          const minhasOrdens = ordensAbertas.filter(o => o.responsavel === me.value?.id).length;
          const ordensSemTecnico = ordensAbertas.filter(o => !o.responsavel).length;

          kpis.value = {
            total_equipamentos: lists.equipamentos.length,
            alertas_ativos: dashAlerts.value.length,
            ordens_abertas: ordensAbertas.length,
            ordens_sem_tecnico: ordensSemTecnico,
            minhas_ordens: minhasOrdens,
          };
        } else {
          const summary = dashboardSummary.value;
          kpis.value = {
            total_equipamentos: summary?.resumo_status?.total ?? lists.equipamentos.length,
            alertas_ativos: summary?.alertas_ativos?.total ?? dashAlerts.value.length,
            ordens_abertas: summary?.os_abertas ?? lists.ordens.filter(o => o.status === 'pendente' || o.status === 'andamento').length,
            leituras_hoje: leiturasTodayCount.value,
            leituras_total: leiturasTotalCount.value || lists.leituras.length,
          };
        }

        if (!isTecnico.value) {
          await fetchTrendAlerts();
        }

        // Busca localizações para filtro de setor no custo
        api('/api/localizacao/?limit=999').then(d => { if (d) lists.localizacoes = normList(d); }).catch(() => { });

      } catch { toast('Erro ao carregar dashboard', 'error'); }
    }

    async function fetchTrendAlerts() {
      try {
        const data = await api('/api/telemetria/tendencias/');
        if (Array.isArray(data)) {
          trendAlerts.value = data;
        }
      } catch (err) {
        console.error('Erro ao buscar tendências:', err);
      }
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

    async function openTrendConfig(sensorId, equipamentoId) {
      trendConfigModal.sensorId = sensorId;
      trendConfigModal.equipamentoId = equipamentoId;
      trendConfigModal.loading = true;
      trendConfigModal.open = true;
      trendConfigModal.isGlobal = false;
      
      try {
        // Fetch specific config
        const data = await api(`/api/telemetria/trend-config/?sensor=${sensorId}`);
        const results = normList(data);
        if (results && results.length > 0) {
          const config = results[0];
          trendConfigModal.form = {
            id: config.id,
            periodo_horas: config.periodo_horas,
            num_leituras: config.num_leituras,
            sensibilidade: config.sensibilidade,
          };
          trendConfigModal.isGlobal = false;
        } else {
          // Defaults if no specific config
          trendConfigModal.form = { periodo_horas: 24, num_leituras: 50, sensibilidade: 'media' };
          trendConfigModal.isGlobal = true;
        }
      } catch (err) {
        toast('Erro ao carregar configuração de tendência', 'error');
      } finally {
        trendConfigModal.loading = false;
      }
    }

    async function saveTrendConfig() {
      trendConfigModal.saving = true;
      try {
        const payload = {
          sensor: trendConfigModal.sensorId,
          periodo_horas: trendConfigModal.form.periodo_horas,
          num_leituras: trendConfigModal.form.num_leituras,
          sensibilidade: trendConfigModal.form.sensibilidade,
          ativo: true
        };
        
        let url = '/api/telemetria/trend-config/';
        let method = 'POST';
        
        if (trendConfigModal.form.id) {
          url += `${trendConfigModal.form.id}/`;
          method = 'PUT';
        }
        
        await api(url, { method, body: JSON.stringify(payload) });
        toast('Configuração de tendência salva', 'success');
        trendConfigModal.open = false;
        
        // Refresh trend data if open
        if (equipModal.open) {
          fetchTrendForSensor(trendConfigModal.sensorId);
        }
      } catch (err) {
        toast('Erro ao salvar configuração', 'error');
      } finally {
        trendConfigModal.saving = false;
      }
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

    async function fetchAlertas() {
      await withLoading(async () => {
        const p = new URLSearchParams();
        if (filters.alertas.search) p.set('search', filters.alertas.search);
        if (filters.alertas.nivel) p.set('nivel', filters.alertas.nivel);
        if (filters.alertas.status) p.set('status', filters.alertas.status);
        if (globalEmpresa.value) p.set('equipamento__empresa', globalEmpresa.value);
        const d = await api('/api/alertas/?' + p);
        let items = normList(d);
        // Filtro por empresa: filtra client-side via IDs de equipamentos da empresa
        sortByNivel(items);
        lists.alertas = items;
        Object.assign(pages.alertas, normPages(d));
        // Busca localizações para mostrar o setor/local de cada equipamento
        const locRes = await api('/api/localizacao/?limit=999');
        if (locRes) lists.localizacoes = normList(locRes);
        // Busca ordens para o botão 'Assumir O.S.' do técnico
        await fetchOrdensAll();
      });
    }

    async function fetchOrdens() {
      await withLoading(async () => {
        const p = new URLSearchParams();
        if (filters.ordens.search) p.set('search', filters.ordens.search);
        if (filters.ordens.status) p.set('status', filters.ordens.status);
        if (filters.ordens.prioridade) p.set('prioridade', filters.ordens.prioridade);
        if (filters.ordens.tipo_os) p.set('tipo_os', filters.ordens.tipo_os);
        if (globalEmpresa.value) p.set('equipamento__empresa', globalEmpresa.value);
        const d = await api('/api/ordens-servico/?' + p);
        let items = normList(d);
        sortByNivel(items, 'prioridade');
        lists.ordens = items;
        if (!lists.usuarios.length) await fetchUsuariosAll();
        Object.assign(pages.ordens, normPages(d));
      });
    }

    async function fetchTelemetria() {
      await withLoading(async () => {
        const ps = new URLSearchParams();
        if (filters.telemetria_sensores.search) ps.set('search', filters.telemetria_sensores.search);
        if (filters.telemetria_sensores.tipo) ps.set('tipo', filters.telemetria_sensores.tipo);
        if (filters.telemetria_sensores.ativo !== '') ps.set('ativo', filters.telemetria_sensores.ativo);
        if (globalEmpresa.value) ps.set('equipamento__empresa', globalEmpresa.value);

        const pl = new URLSearchParams();
        if (filters.telemetria_leituras.valor_min) pl.set('valor_min', filters.telemetria_leituras.valor_min);
        if (filters.telemetria_leituras.valor_max) pl.set('valor_max', filters.telemetria_leituras.valor_max);
        if (filters.telemetria_leituras.timestamp_de) pl.set('timestamp_de', filters.telemetria_leituras.timestamp_de);
        if (filters.telemetria_leituras.timestamp_ate) pl.set('timestamp_ate', filters.telemetria_leituras.timestamp_ate);

        const [s, l] = await Promise.all([
          api('/api/telemetria/sensores/?' + ps),
          api('/api/telemetria/leituras/?' + pl + (pl.toString() ? '&' : '') + 'ordering=-timestamp'),
        ]);
        let sItems = normList(s);
        let lItems = normList(l);
        lists.sensores = sItems;
        Object.assign(pages.sensores, normPages(s));
        lists.leituras = lItems;
        Object.assign(pages.leituras, normPages(l));
      });
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

    async function fetchPrompts() {
      await withLoading(async () => {
        const d = await api('/api/gemini/prompts/');
        lists.prompts = d.map(p => ({
          ...p,
          edit_text: p.custom_text || p.original_text
        }));
      });
    }

    async function savePrompt(promptId, customText) {
      try {
        await api(`/api/gemini/prompts/${promptId}/`, {
          method: 'PATCH',
          body: JSON.stringify({ custom_text: customText })
        });
        showToast('Prompt salvo com sucesso!', 'success');
        fetchPrompts();
      } catch (e) {
        showToast('Erro ao salvar prompt', 'error');
      }
    }

    async function resetPrompt(promptId) {
      if (!confirm('Tem certeza que deseja restaurar o prompt original?')) return;
      try {
        await api(`/api/gemini/prompts/${promptId}/reset/`, { method: 'POST' });
        showToast('Prompt restaurado para o original!', 'success');
        fetchPrompts();
      } catch (e) {
        showToast('Erro ao restaurar prompt', 'error');
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
      if (lists.empresas.length) return;
      const d = await api('/api/empresas/?limit=999');
      lists.empresas = normList(d);
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
      if (lists.usuarios.length) return;
      const d = await api('/api/usuarios/?limit=999');
      const items = normList(d);
      sortByTipoUsuario(items);
      lists.usuarios = items;
    }

    async function fetchPage(resource, url) {
      if (!url) return;
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
        defaults: { nome: '', tipo: '', modelo: '', fabricante: '', numero_serie: '', status: 'ativo', criticidade: null, justificativa_criticidade: '', empresa: null, data_instalacao: '', descricao: '' }
      },
      alerta: {
        title: 'Alerta', endpoint: '/api/alertas/',
        defaults: { tipo_alerta: '', nivel: 'medio', descricao: '', status: 'ativo', equipamento: null }
      },

      ordem: {
        title: 'Ordem de Serviço', endpoint: '/api/ordens-servico/',
        defaults: { titulo: '', tipo_os: 'preventiva', prioridade: 'media', gravidade_condicao: 'ausente', risco_seguranca: false, status: 'pendente', equipamento: null, responsavel: null, descricao: '', custo_pecas: null, custo_mao_de_obra: null }
      },
      encerrar_os: {
        title: 'Encerrar O.S.', endpoint: '/api/ordens-servico/',
        defaults: { titulo: '', tipo_os: 'preventiva', prioridade: 'media', status: 'concluida', equipamento: null, responsavel: null, descricao: '', custo_pecas: null, custo_mao_de_obra: null }
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

      modal.open = true;
      if (['equipamento', 'alerta', 'ordem', 'sensor', 'localizacao', 'leitura'].includes(type)) {
        await fetchEquipamentosAll();
        await fetchEmpresasAll();
      }
      if (type === 'ordem') await fetchUsuariosAll();
      if (type === 'leitura') await fetchSensoresAll();
      if (type === 'usuario') await fetchEmpresasAll();
      if (type === 'historico') await fetchOrdensAll(); // Histórico precisa das ordens
    }

    async function editItem(type, item) {
      const cfg = modalConfig[type];
      modal.type = type; modal.title = 'Editar ' + cfg.title;
      modal.editId = item.id; modal.oldStatus = item.status; formErrors.value = {};
      resetForm({ ...cfg.defaults, ...item }); modal.open = true;

      if (['equipamento', 'alerta', 'ordem', 'sensor', 'localizacao', 'leitura'].includes(type)) {
        await fetchEquipamentosAll();
        await fetchEmpresasAll();
      }
      if (type === 'ordem') await fetchUsuariosAll();
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
          const prioridadesValidas = ['baixa', 'media', 'alta', 'critica'];
          const statusValidos = ['pendente', 'andamento', 'concluida', 'cancelada'];
          const tiposValidos = ['preventiva', 'corretiva', 'preditiva'];
          if (!prioridadesValidas.includes(payload.prioridade)) payload.prioridade = 'media';
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
          const alertaAutomatico = modal.type === 'alerta' && fd.origem !== 'manual';
          await api(cfg.endpoint + modal.editId + '/', {
            method: alertaAutomatico ? 'PATCH' : 'PUT',
            body: JSON.stringify(alertaAutomatico ? { status: payload.status } : payload),
          });
        } else {
          const res = await api(cfg.endpoint, { method: 'POST', body: JSON.stringify(payload) });
          if ((modal.type === 'ordem' || modal.type === 'encerrar_os') && res) createdOsId = res.id;
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
        await api('/api/ordens-servico/' + o.id + '/', { method: 'PATCH', body: JSON.stringify(payload) });
        toast('O.S. assumida com sucesso!', 'success');
        o.responsavel = me.value.id;
        if (payload.status) o.status = payload.status;
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
        await api('/api/ordens-servico/' + o.id + '/', { method: 'PATCH', body: JSON.stringify(payload) });
        toast('Atendimento iniciado!', 'success');
        o.responsavel = me.value.id;
        o.status = 'andamento';
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

    async function assumirOSFromAlerta(alerta) {
      if (!alerta.ordem_servico_id) {
        toast('Este alerta não possui O.S. vinculada.', 'error');
        return;
      }
      try {
        const os = await api('/api/ordens-servico/' + alerta.ordem_servico_id + '/');
        if (['concluida', 'cancelada'].includes(os.status) || os.responsavel) {
          toast('A O.S. vinculada está encerrada ou já possui responsável.', 'error');
          return;
        }
        await assumirOS(os);
        navigate(view.value);
      } catch {
        toast('Não foi possível acessar a O.S. vinculada.', 'error');
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
            title: 'Alertas',
            subtitle: `Gerado em: ${now}`,
            columns: ['ID', 'Tipo', 'Nível', 'Descrição', 'Equipamento', 'Status', 'Data'],
            rows: lists.alertas.map(a => [
              a.id, a.tipo_alerta, a.nivel, a.descricao || '—',
              eqNome(a.equipamento), a.status, fmtDate(a.data_alerta)
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
            ['Alertas Ativos', k.alertas_ativos ?? '—'],
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
        if (filters.alertas.nivel) p.set('nivel', filters.alertas.nivel);
        if (filters.alertas.status) p.set('status', filters.alertas.status);
        if (globalEmpresa.value) p.set('empresa', globalEmpresa.value);
      } else if (resource === 'ordens-servico') {
        if (filters.ordens.status) p.set('status', filters.ordens.status);
        if (filters.ordens.prioridade) p.set('prioridade', filters.ordens.prioridade);
        if (filters.ordens.tipo_os) p.set('tipo_os', filters.ordens.tipo_os);
        if (globalEmpresa.value) p.set('empresa', globalEmpresa.value);
      } else if (resource === 'historico') {
        if (filters.historico.data_de) p.set('data_execucao_depois', filters.historico.data_de);
        if (filters.historico.data_ate) p.set('data_execucao_antes', filters.historico.data_ate);
        if (globalEmpresa.value) p.set('empresa', globalEmpresa.value);
      } else if (resource === 'telemetria') {
        if (globalEmpresa.value) p.set('empresa', globalEmpresa.value);
      } else if (resource === 'dashboard') {
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
    function prioridadeBadge(p) { return { critica: 'badge-red', alta: 'badge-orange', media: 'badge-yellow', baixa: 'badge-green' }[p] || 'badge-gray'; }
    function prioridadeIcon(p) { return { critica: '🔴', alta: '🟠', media: '🟡', baixa: '🟢' }[p] || '⚪'; }
    function prioridadeLabel(p) { return { critica: 'Crítica', alta: 'Alta', media: 'Média', baixa: 'Baixa' }[p] || '—'; }

    function makeLineChart(readings, W = 360, H = 180) {
      const raw = Array.isArray(readings) ? readings.slice(0, 20).reverse() : [];
      if (!raw.length) return { path: '', area: '', dots: [], ticks: [], min: 0, max: 0 };
      const values = raw.map(l => parseFloat(l.valor) || 0);
      const min = Math.min(...values);
      const max = Math.max(...values);
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
      return { path, area, dots: points, ticks, min: min.toFixed(2), max: max.toFixed(2) };
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
        sortByNivel(equipModal.ordens, 'prioridade'); // Ordem de prioridade (crítico > médio > baixo)
      } catch (err) {
        equipModal.ordens = [];
        console.error("Erro ao buscar ordens do equipamento", err);
      }
    }

    async function pollEquipamentoReadings() {
      if (!equipModal.open || !equipModal.selectedSensor) return;
      await fetchEquipamentoReadings(equipModal.selectedSensor, { silent: true });
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

    async function openEquipamentoDetails(eq, os = null) {
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
      equipModal.currentOS = os || null;
      equipModal.selectedSensor = null;
      equipModal.readings = [];
      equipModal.error = '';
      equipModal.refreshing = false;
      equipModal.ordens = [];
      equipModal.osFilter = os ? 'os' : 'todas';
      await fetchEquipamentoSensors(equipment.id);
      fetchEquipamentoOrdens(equipment.id);
      if (equipModal.sensors.length) {
        equipModal.selectedSensor = equipModal.sensors[0].id;
      }
      pollEquipamentoReadings();
    }

    function closeEquipModal() {
      equipModal.open = false;
      equipModal.equipamento = null;
      equipModal.currentOS = null;
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
        await fetchEquipamentoReadings(sensorId);
        stopEquipModalPolling();
        pollEquipamentoReadings();
      }
    });

    function eqNome(id) {
      if (id == null) return '—';
      const eq = lists.equipamentos.find(e => e.id === id);
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
      // Recarrega a aba atual ao mudar o filtro global
      // Também recarrega o dashboard se estiver nele
      const currentView = view.value;
      if (currentView === 'dashboard') {
        fetchDashboard();
      } else {
        fetchers[currentView]?.();
      }
    }

    // ─── ATUALIZAÇÃO AUTOMÁTICA SILENCIOSA (OTIMIZADA) ───
    onMounted(async () => {
      // Adicionar listener para fechar janelas com ESC
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
          if (modal.open) modal.open = false;
          else if (equipModal.open) closeEquipModal();
          else if (chatOpen.value) chatOpen.value = false;
        }
      });

      if (token.value) {
        await fetchMe();
        // Carrega lista de empresas para o filtro global do admin
        await fetchEmpresasAll();
        navigate('dashboard');
      }

      // ─── ATUALIZAÇÃO AUTOMÁTICA SILENCIOSA (OTIMIZADA) ───
      setInterval(async () => {
        // Só tenta buscar se o usuário estiver logado
        if (token.value) {
          try {
            if (view.value === 'dashboard') {
              const today = new Date().toISOString().slice(0, 10);
              const timestampDe = `${today}T00:00:00`;
              const timestampAte = `${today}T23:59:59`;
              const telUrl = buildTelemetriaUrl({
                limit: 50,
                allowedEqIds: dashboardAllowedEquipamentoIds.value,
                sensorId: dashTelemetriaSensor.value,
                equipamentoId: dashTelemetriaEquip.value,
              });

              const [telRes, telHojeRes, telTotalRes, alertRes] = await Promise.allSettled([
                api(telUrl),
                api(buildTelemetriaUrl({
                  limit: 1,
                  allowedEqIds: dashboardAllowedEquipamentoIds.value,
                  timestampDe,
                  timestampAte,
                })),
                api(buildTelemetriaUrl({
                  limit: 1,
                  allowedEqIds: dashboardAllowedEquipamentoIds.value,
                })),
                api('/api/alertas/?status=ativo&limit=50&ordering=-criado_em')
              ]);

              // Atualiza os gráficos de forma dinâmica e reativa sem travar a tela
              if (telRes.status === 'fulfilled') {
                let leituras = normList(telRes.value);
                // Se filtro por equipamento (sem sensor específico), filtra client-side
                if (dashTelemetriaEquip.value && !dashTelemetriaSensor.value) {
                  const eqId = Number(dashTelemetriaEquip.value);
                  const sensorIds = new Set(lists.sensores.filter(s => getEquipamentoId(s.equipamento) === eqId).map(s => s.id));
                  leituras = leituras.filter(l => sensorIds.has(l.sensor));
                }
                // Se empresa global ativa, filtra pelos sensores conhecidos
                if (globalEmpresa.value && !dashTelemetriaSensor.value) {
                  const filterIds = new Set(lists.sensores.map(s => s.id));
                  leituras = leituras.filter(l => filterIds.has(l.sensor));
                }
                lists.leituras = leituras;
              }
              if (telTotalRes.status === 'fulfilled' && telTotalRes.value) {
                leiturasTotalCount.value = Number(telTotalRes.value.count ?? 0) || lists.leituras.length;
                if (kpis.value) kpis.value.leituras_total = leiturasTotalCount.value;
              }
              if (telHojeRes.status === 'fulfilled' && telHojeRes.value) {
                leiturasTodayCount.value = Number(telHojeRes.value.count ?? 0) || 0;
                if (kpis.value) kpis.value.leituras_hoje = leiturasTodayCount.value;
              }
              if (alertRes.status === 'fulfilled') {
                const alertItems = normList(alertRes.value);
                sortByNivel(alertItems);
                lists.alertas = alertItems;
                alertCount.value = lists.alertas.length;
                dashAlerts.value = lists.alertas.slice(0, 5);
              }
            }
            else if (view.value === 'telemetria') {
              // Atualiza a tabela de leituras sem disparar a tela de loading global
              const pl = new URLSearchParams();
              if (filters.telemetria_leituras.valor_min) pl.set('valor_min', filters.telemetria_leituras.valor_min);
              if (filters.telemetria_leituras.valor_max) pl.set('valor_max', filters.telemetria_leituras.valor_max);
              const res = await api('/api/telemetria/leituras/?' + pl + (pl.toString() ? '&' : '') + 'ordering=-timestamp');
              if (res) lists.leituras = normList(res);
            }
            else if (view.value === 'alertas') {
              // Atualização silenciosa — reutiliza os filtros ativos do usuário
              const p = new URLSearchParams();
              if (filters.alertas.search) p.set('search', filters.alertas.search);
              if (filters.alertas.nivel) p.set('nivel', filters.alertas.nivel);
              if (filters.alertas.status) p.set('status', filters.alertas.status);
              const res = await api('/api/alertas/?' + p);
              if (res) { const items = normList(res); sortByNivel(items); lists.alertas = items; }
            }
          } catch (e) {
            console.warn("Pequeno atraso na sincronização, tentando no próximo ciclo...");
          }
        }
      }, 10000); // 10 segundos — sincroniza em tempo real sem sobrecarregar
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
        promptText = 'Quais os passos recomendados para consertar e analisar a causa raiz dos alertas críticos mais recentes?';
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
        promptText = 'Quais são os alertas críticos globais que exigem intervenção macro ou escalonamento imediato?';
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
      token, me, view, loading, loginLoading, loginError, loginForm,
      kpis, dashAlerts, alertCount, toasts, lists, pages, filters,
      modal, fd, formErrors, globalEmpresa,
      isAdmin, isAdminOrGestor, isTecnico, userInitial, viewTitle, osSemTecnicoCount,
      doLogin, logout, navigate, debouncedFetch,
      fetchEquipamentos, fetchAlertas, fetchOrdens, fetchTelemetria,
      fetchHistorico, fetchEmpresas, fetchUsuarios, fetchLocalizacoes, fetchPrompts, fetchPage, fetchDashboard,
      openModal, editItem, saveItem, deleteItem, exportData, assumirOS, iniciarAtendimento, openEncerrarOS, assumirOSFromAlerta,
      formatNumber, fmtDate, nivelBadge, nivelColor, statusBadge, eqStatusBadge,
      ordemStatusBadge, prioridadeBadge, prioridadeIcon, prioridadeLabel,
      eqNome, getEquipamentoInfo, osTitulo, osEquipNome, eqEmpresaNome, empresaNome, sensorNome, locSetor, custoTotal, countSensores, usuarioNome,
      empresaNomeSensor, sensorEquipNome,
      onGlobalEmpresaChange,
      chartEquipStatus, chartAlertNivel, chartOrdens, chartTelemetria, chartCustoEvolucao,
      telemetriaSummary, telemetryMovingDot, displayedChartTelemetria, telemetrySlideOffset,
      dashboardEquipamentos,
      dashAlertsCollapsed, dashOrdensCollapsed, filtroFilaPrioridade, ordensFilaPrioridade,
      donutArcs,
      availableSectors,
      leiturasHoje, leiturasTodayCount, leiturasTotalCount, dashTelemetriaEquip, dashTelemetriaSensor,
      dashTelemetriaSensoresFiltrados, dashCustoSetor,
      dashSetor, dashEquipamento, explainerCollapsed, dashboardMetrics, dashboardEquipmentOptions, availableDashboardSectors, dashboardKpisLoading, dashboardKpisError,
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
