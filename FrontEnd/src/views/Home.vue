<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';
import { 
  Chart as ChartJS, 
  Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, ArcElement 
} from 'chart.js';
import { Bar, Doughnut } from 'vue-chartjs';

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale, ArcElement);

const router = useRouter();

const user = ref(null);
const dashboardData = ref(null);
const empresas = ref([]);
const selectedEmpresa = ref('');
const searchQuery = ref('');
const isLoading = ref(true);
const showHelp = ref(false); 

const loadInitial = async () => {
  try {
    const meRes = await api.get('auth/me/');
    user.value = meRes.data;
    
    if (user.value.tipo_usuario === 'admin') {
      const empRes = await api.get('empresas/');
      empresas.value = empRes.data.results || empRes.data;
    }
    
    await loadDashboard();
  } catch (error) {
    console.error("Erro no setup inicial:", error);
  } finally {
    isLoading.value = false;
  }
};

const loadDashboard = async () => {
  isLoading.value = true;
  try {
    const url = selectedEmpresa.value 
      ? `dashboards/resumo/?empresa_id=${selectedEmpresa.value}` 
      : 'dashboards/resumo/';
    const res = await api.get(url);
    dashboardData.value = res.data;
  } catch (error) {
    console.error("Erro ao carregar resumo:", error);
  } finally {
    isLoading.value = false;
  }
};

watch(selectedEmpresa, () => {
  loadDashboard();
});

const filteredEquipamentos = computed(() => {
  if (!dashboardData.value) return [];
  const query = searchQuery.value.toLowerCase();
  return dashboardData.value.detalhes_equipamentos.filter(d => 
    d.equipamento.toLowerCase().includes(query)
  );
});

const getHealthColor = (val) => {
  if (val >= 95) return '#10b981';
  if (val >= 80) return '#f59e0b';
  return '#ef4444';
};

// Navegação Programática
const goToTelemetria = (equipamentoId) => {
  router.push({ name: 'Telemetria', query: { id: equipamentoId } });
};

const goToManutencao = (equipamentoId) => {
  router.push({ name: 'Manutencao', query: { id: equipamentoId } });
};

// Configurações Globais de Animação Chart.js (Efeito Elástico)
const chartAnimations = {
  duration: 2000,
  easing: 'easeOutElastic',
  delay: (context) => context.dataIndex * 150
};

const barOptions = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  animation: chartAnimations,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      padding: 12,
      cornerRadius: 10,
      titleFont: { size: 14, weight: 'bold' }
    }
  },
  scales: {
    x: { 
      min: 0, max: 100,
      grid: { color: 'rgba(255,255,255,0.03)' },
      ticks: { color: '#64748b', font: { weight: 'bold' } }
    },
    y: { 
      grid: { display: false },
      ticks: { color: '#94a3b8', font: { size: 12, weight: '600' } }
    }
  }
};

const barChartData = computed(() => {
  const det = filteredEquipamentos.value;
  return {
    labels: det.map(d => d.equipamento),
    datasets: [{
      label: 'Saúde Operacional',
      backgroundColor: det.map(d => getHealthColor(d.disponibilidade_porcentagem)),
      borderRadius: 6,
      data: det.map(d => Math.min(100, d.disponibilidade_porcentagem))
    }]
  };
});

const doughnutData = computed(() => {
  if (!dashboardData.value) return { labels: [], datasets: [] };
  const s = dashboardData.value.resumo_status;
  return {
    labels: ['Operando', 'Manutenção', 'Inativo'],
    datasets: [{
      backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
      hoverBackgroundColor: ['#34d399', '#fbbf24', '#f87171'],
      borderWidth: 0,
      hoverOffset: 20,
      data: [s.ativo, s.manutencao, s.inativo]
    }]
  };
});

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: {
    animateRotate: true,
    animateScale: true,
    duration: 1500,
    easing: 'easeInOutQuart'
  },
  plugins: {
    legend: { display: false }
  },
  cutout: '80%'
};

onMounted(() => {
  loadInitial();
});
</script>

<template>
  <div class="home-view">
    <!-- Header Interativo -->
    <div class="dashboard-header animate-in">
      <div class="title-group">
        <h2>Dashboard Executivo Industrial</h2>
        <div class="subtitle-badge">
           <span class="dot pulse-green"></span> 
           Live Monitoring: {{ new Date().toLocaleDateString('pt-BR') }}
        </div>
      </div>

      <div class="admin-controls">
        <button class="btn-help-ios" @click="showHelp = !showHelp">
          <svg class="icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          Guia Técnico
        </button>
        <div class="filter-glass" v-if="user?.tipo_usuario === 'admin'">
          <select v-model="selectedEmpresa" class="modern-select">
            <option value="">Consolidado Global</option>
            <option v-for="emp in empresas" :key="emp.id" :value="emp.id">{{ emp.nome }}</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Guia de Ajuda com Design Apple-Style -->
    <transition name="expand">
      <div v-if="showHelp" class="help-shelf glass-panel">
        <div class="help-header">
           <h4>Glossário de Engenharia de Confiabilidade</h4>
           <button class="close-btn" @click="showHelp = false">✕</button>
        </div>
        <div class="help-grid">
          <div class="help-card-inner">
            <div class="h-icon-box bg-success-soft"><svg class="icon-18" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg></div>
            <h6>Saúde Operacional</h6>
            <p>Mede a disponibilidade real. Meta recomendada: <strong>> 95.5%</strong>.</p>
          </div>
          <div class="help-card-inner">
            <div class="h-icon-box bg-warning-soft"><svg class="icon-18" viewBox="0 0 24 24" fill="none" stroke="currentColor"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></div>
            <h6>MTTR (Response)</h6>
            <p>Tempo médio p/ reparo. Quanto <strong>menor</strong>, mais ágil é sua equipe.</p>
          </div>
          <div class="help-card-inner">
            <div class="h-icon-box bg-primary-soft"><svg class="icon-18" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg></div>
            <h6>MTBF (Stability)</h6>
            <p>Confiabilidade. Quanto <strong>maior</strong>, mais tempo a máquina produz sem falhas.</p>
          </div>
        </div>
      </div>
    </transition>

    <div v-if="isLoading" class="loading-full">
      <div class="spinner-premium"></div>
      <p>Sincronizando Ativos Industriais...</p>
    </div>

    <div v-else-if="dashboardData" class="dashboard-content animate-fade-up">
      <!-- KPI Cards with 3D Tilt Effect -->
      <div class="kpi-grid">
        <div class="kpi-card glass-panel tilt" :style="{ borderColor: getHealthColor(dashboardData.kpis_globais.disponibilidade_media) }">
          <div class="kpi-visual">
            <div class="kpi-ring" :style="{ borderTopColor: getHealthColor(dashboardData.kpis_globais.disponibilidade_media) }"></div>
            <span class="kpi-val">{{ Math.min(100, dashboardData.kpis_globais.disponibilidade_media) }}%</span>
          </div>
          <div class="kpi-info">
            <span class="kpi-label">Saúde Geral Planta</span>
            <div class="kpi-benchmark">
              <span class="b-tag" :class="dashboardData.kpis_globais.disponibilidade_media > 90 ? 'b-ok' : 'b-warn'">
                {{ dashboardData.kpis_globais.disponibilidade_media > 90 ? 'ALTA PERFORMANCE' : 'ATENÇÃO REQUERIDA' }}
              </span>
            </div>
          </div>
        </div>

        <div class="kpi-card glass-panel tilt">
          <div class="kpi-top">
            <span class="kpi-circle-icon bg-warning-glow"><svg class="w-20" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg></span>
            <span class="kpi-val-alt">{{ dashboardData.kpis_globais.mttr_medio }}h</span>
          </div>
          <p class="kpi-label-alt">MTTR Geral Médio</p>
          <div class="kpi-mini-graph">
            <div class="mini-bar-bg"><div class="mini-bar-fill warn" style="width: 45%;"></div></div>
          </div>
        </div>

        <div class="kpi-card glass-panel tilt">
          <div class="kpi-top">
            <span class="kpi-circle-icon bg-primary-glow"><svg class="w-20" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></span>
            <span class="kpi-val-alt">{{ dashboardData.kpis_globais.mtbf_medio }}h</span>
          </div>
          <p class="kpi-label-alt">MTBF Confiabilidade</p>
          <div class="kpi-mini-graph">
            <div class="mini-bar-bg"><div class="mini-bar-fill primary" style="width: 78%;"></div></div>
          </div>
        </div>

        <div class="kpi-card glass-panel tilt">
          <div class="kpi-top">
            <span class="kpi-circle-icon bg-success-glow"><svg class="w-20" viewBox="0 0 24 24" fill="none" stroke="currentColor"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg></span>
            <span class="kpi-val-alt">{{ dashboardData.resumo_status.total }}</span>
          </div>
          <p class="kpi-label-alt">Total Ativos Monitorados</p>
          <div class="kpi-mini-graph">
             <div class="mini-dots">
               <span v-for="n in 5" :key="n" class="m-dot active"></span>
             </div>
          </div>
        </div>
      </div>

      <!-- Área de Insights -->
      <div class="main-stats-row">
        <div class="analytics-box glass-panel expand">
          <div class="box-header">
            <div class="box-title">
              <h4>Engenharia de Disponibilidade</h4>
              <p>Análise de saúde por equipamento (90 dias)</p>
            </div>
            <div class="box-actions">
              <div class="modern-search">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="search-icon"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input v-model="searchQuery" type="text" placeholder="Pesquisar ativo..." />
              </div>
            </div>
          </div>
          
          <div class="chart-viewport">
            <Bar :data="barChartData" :options="barOptions" />
          </div>
        </div>

        <div class="status-summary-box glass-panel">
          <div class="box-header">
            <h4>Status da Frota</h4>
            <span class="badge-blue">LIVE</span>
          </div>
          <div class="doughnut-container">
            <Doughnut :data="doughnutData" :options="doughnutOptions" />
            <div class="doughnut-center-info">
               <span class="d-total">{{ dashboardData.resumo_status.total }}</span>
               <span class="d-label">EQUIP.</span>
            </div>
          </div>
          <div class="status-legend-modern">
            <div class="l-item">
              <span class="l-strip bg-success"></span>
              <div class="l-info">
                <span class="l-count">{{ dashboardData.resumo_status.ativo }}</span>
                <span class="l-name">Operacional</span>
              </div>
            </div>
            <div class="l-item">
              <span class="l-strip bg-warning"></span>
              <div class="l-info">
                <span class="l-count">{{ dashboardData.resumo_status.manutencao }}</span>
                <span class="l-name">Em Manutenção</span>
              </div>
            </div>
            <div class="l-item">
              <span class="l-strip bg-danger"></span>
              <div class="l-info">
                <span class="l-count">{{ dashboardData.resumo_status.inativo }}</span>
                <span class="l-name">Fora de Serviço</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Tabela Elevada -->
      <div class="table-container-glass animate-fade-up-slow">
        <div class="table-toolbar">
           <h4>Snapshot Técnico</h4>
           <p>Métricas consolidadas de Lifecycle</p>
        </div>
        <div class="table-scroll">
          <table class="table-premium">
            <thead>
              <tr>
                <th>Nome do Ativo</th>
                <th>Estado Real</th>
                <th>MTTR (Reparo)</th>
                <th>MTBF (Média)</th>
                <th class="text-center">Histórico O.S</th>
                <th>Performance</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in filteredEquipamentos" :key="d.equipamento_id" class="table-row-hover clickable" @click="goToTelemetria(d.equipamento_id)">
                <td>
                  <div class="item-name">
                    <div class="item-icon-small"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" class="w-16"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg></div>
                    <span>{{ d.equipamento }}</span>
                  </div>
                </td>
                <td>
                  <span class="badge-status" :class="d.status">
                    <span class="status-dot"></span>
                    {{ d.status }}
                  </span>
                </td>
                <td class="font-mono text-dim">{{ d.mttr_hours }}h</td>
                <td class="font-mono text-dim">{{ d.mtbf_hours }}h</td>
                <td class="text-center">
                  <span class="badge-count hover-highlight" @click.stop="goToManutencao(d.equipamento_id)">
                    {{ d.total_manutencoes }}
                  </span>
                </td>
                <td>
                  <div class="perf-bar-group">
                    <span class="perf-val" :style="{ color: getHealthColor(d.disponibilidade_porcentagem) }">{{ d.disponibilidade_porcentagem }}%</span>
                    <div class="perf-bar-bg"><div class="perf-bar-fill" :style="{ width: d.disponibilidade_porcentagem + '%', backgroundColor: getHealthColor(d.disponibilidade_porcentagem) }"></div></div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-view { display: flex; flex-direction: column; gap: 2rem; }

/* Animações Iniciais */
.animate-in { animation: slideDown 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
.animate-fade-up { animation: fadeUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
.animate-fade-up-slow { animation: fadeUp 1s cubic-bezier(0.2, 0.8, 0.2, 1) 0.2s both; }

@keyframes slideDown { from { opacity: 0; transform: translateY(-20px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }

/* Header */
.dashboard-header { display: flex; justify-content: space-between; align-items: flex-start; }
.title-group h2 { font-size: 2.2rem; font-weight: 800; letter-spacing: -1.5px; margin-bottom: 0.5rem; }
.subtitle-badge { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 1rem; background: rgba(255,255,255,0.03); border-radius: 30px; font-size: 0.75rem; font-weight: 700; color: #94a3b8; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.pulse-green { background: #10b981; box-shadow: 0 0 10px #10b981; animation: pulse 2s infinite; }
@keyframes pulse { 0% { transform: scale(0.95); opacity: 1; } 70% { transform: scale(1.3); opacity: 0; } 100% { transform: scale(0.95); opacity: 0; } }

.admin-controls { display: flex; gap: 1rem; }
.btn-help-ios { 
  display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.2rem; 
  background: white; color: black; border-radius: 12px; font-size: 0.85rem; font-weight: 700;
  transition: 0.3s; cursor: pointer; border: none;
}
.btn-help-ios:hover { transform: translateY(-2px); box-shadow: 0 10px 20px rgba(255,255,255,0.1); }

/* KPI Grid */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem; }
.kpi-card { 
  padding: 1.5rem; display: flex; gap: 1.5rem; align-items: center; 
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  cursor: default; border-left: 1px solid rgba(255,255,255,0.1) !important;
}
.kpi-card:hover { transform: translateY(-8px) scale(1.02); background: rgba(30, 41, 59, 0.6); box-shadow: 0 20px 40px rgba(0,0,0,0.4); }

.kpi-visual { position: relative; width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; }
.kpi-ring { position: absolute; inset: 0; border: 6px solid rgba(255,255,255,0.05); border-radius: 50%; border-top: 6px solid #10b981; }
.kpi-val { font-size: 1.2rem; font-weight: 900; }

.kpi-top { display: flex; justify-content: space-between; align-items: center; width: 100%; margin-bottom: 1rem; }
.kpi-circle-icon { width: 44px; height: 44px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; }
.bg-warning-glow { background: #f59e0b; box-shadow: 0 0 20px rgba(245, 158, 11, 0.3); }
.bg-primary-glow { background: #3b82f6; box-shadow: 0 0 20px rgba(59, 130, 246, 0.3); }
.bg-success-glow { background: #10b981; box-shadow: 0 0 20px rgba(16, 185, 129, 0.3); }
.kpi-val-alt { font-size: 1.8rem; font-weight: 800; }
.kpi-label-alt { font-size: 0.8rem; font-weight: 600; color: #64748b; margin-bottom: 0.5rem; }

/* Help Shelf */
.help-shelf { padding: 2rem; background: rgba(15, 23, 42, 0.95); margin-bottom: 1rem; }
.help-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
.help-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
.help-card-inner { padding: 1.5rem; background: rgba(255,255,255,0.02); border-radius: 16px; border: 1px solid rgba(255,255,255,0.05); }
.h-icon-box { width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-bottom: 1rem; }
.bg-success-soft { background: rgba(16, 185, 129, 0.1); color: #10b981; }

/* Main Analytics Row */
.main-stats-row { display: grid; grid-template-columns: 1fr 340px; gap: 1.5rem; }
.chart-viewport { height: 400px; padding-top: 1rem; }

.doughnut-container { position: relative; height: 260px; margin: 1.5rem 0; }
.doughnut-center-info { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; }
.d-total { font-size: 2.5rem; font-weight: 900; line-height: 1; }
.d-label { font-size: 0.7rem; font-weight: 800; color: #64748b; padding-top: 4px; }

.status-legend-modern { display: flex; flex-direction: column; gap: 1rem; }
.l-item { display: flex; align-items: center; gap: 1rem; background: rgba(255,255,255,0.02); padding: 0.75rem; border-radius: 12px; }
.l-strip { width: 4px; height: 24px; border-radius: 2px; }
.l-info { display: flex; flex-direction: column; }
.l-count { font-size: 1rem; font-weight: 800; }
.l-name { font-size: 0.7rem; font-weight: 600; color: #64748b; }

/* Premium Table */
.table-container-glass { background: rgba(15, 23, 42, 0.4); border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); overflow: hidden; }
.table-toolbar { padding: 1.5rem 2rem; border-bottom: 1px solid rgba(255,255,255,0.05); }
.table-premium { width: 100%; border-collapse: collapse; }
.table-premium th { padding: 1.2rem 2rem; text-align: left; font-size: 0.75rem; font-weight: 800; color: #64748b; text-transform: uppercase; background: rgba(0,0,0,0.2); }
.table-premium td { padding: 1.2rem 2rem; border-bottom: 1px solid rgba(255,255,255,0.03); }
.table-row-hover:hover { background: rgba(255,255,255,0.02); }

.item-name { display: flex; align-items: center; gap: 1rem; font-weight: 700; }
.item-icon-small { width: 32px; height: 32px; border-radius: 8px; background: rgba(59, 130, 246, 0.1); color: #3b82f6; display: flex; align-items: center; justify-content: center; }
.item-icon-small svg { width: 16px; }

.badge-status { display: inline-flex; align-items: center; gap: 0.5rem; padding: 0.4rem 0.8rem; border-radius: 8px; font-size: 0.75rem; font-weight: 700; text-transform: capitalize; }
.badge-status.ativo { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

.font-mono { font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; font-weight: 600; }
.text-dim { color: #94a3b8; }
.badge-count { padding: 0.2rem 0.6rem; background: rgba(255,255,255,0.05); border-radius: 4px; font-weight: 800; transition: 0.2s; }

/* Correção de Ícones Gigantes */
.icon-sm, .icon-18, .search-icon, .w-20 { width: 20px !important; height: 20px !important; flex-shrink: 0; }
.w-16 { width: 16px !important; height: 16px !important; flex-shrink: 0; }

/* Estilos de Clique */
.clickable { cursor: pointer; }
.hover-highlight:hover { background: var(--color-primary) !important; color: white !important; transform: scale(1.1); }

.perf-bar-group { display: flex; align-items: center; gap: 1rem; }
.perf-val { width: 45px; font-weight: 800; font-size: 0.85rem; }
.perf-bar-bg { flex: 1; height: 6px; background: rgba(255,255,255,0.05); border-radius: 10px; }
.perf-bar-fill { height: 100%; border-radius: 10px; transition: width 1.5s cubic-bezier(0.4, 0, 0.2, 1); }

/* Transitions */
.expand-enter-active, .expand-leave-active { transition: all 0.5s ease; max-height: 400px; opacity: 1; }
.expand-enter-from, .expand-leave-to { max-height: 0; opacity: 0; transform: translateY(-20px); }
</style>
