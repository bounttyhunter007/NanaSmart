<script setup>
import { ref, onMounted } from 'vue';
import api from '../services/api';

const alertas = ref([]);
const isLoading = ref(true);
const isOSModalOpen = ref(false);

const osData = ref({
  titulo: '',
  descricao: '',
  equipamento: '',
  prioridade: 'alta', // Por padrão, se vem de um alerta, é alta
  status: 'pendente'
});

const loadAlertas = async () => {
  isLoading.value = true;
  try {
    const response = await api.get('alertas/');
    alertas.value = response.data.results || response.data;
  } catch (error) {
    console.error("Erro ao carregar alertas:", error);
  } finally {
    isLoading.value = false;
  }
};

const abrirModalOS = (alerta) => {
  osData.value = {
    titulo: `Reparo: ${alerta.tipo_alerta}`,
    descricao: `O.S gerada automaticamente a partir do alerta: ${alerta.descricao}`,
    equipamento: alerta.equipamento && alerta.equipamento.id ? alerta.equipamento.id : alerta.equipamento,
    prioridade: alerta.nivel === 'critico' ? 'urgente' : 'alta',
    status: 'pendente',
    alerta_id: alerta.id // Para marcarmos como resolvido depois
  };
  isOSModalOpen.value = true;
};

const criarOSEMarcarResolvido = async () => {
  try {
    // 1. Criar a O.S
    await api.post('ordens-servico/', {
      titulo: osData.value.titulo,
      descricao: osData.value.descricao,
      equipamento: osData.value.equipamento,
      prioridade: osData.value.prioridade,
      status: osData.value.status
    });
    
    // 2. Marcar o alerta como resolvido
    if (osData.value.alerta_id) {
       await api.patch(`alertas/${osData.value.alerta_id}/`, {
         status: 'resolvido'
       });
    }

    isOSModalOpen.value = false;
    alert("Ordem de Serviço gerada e Alerta resolvido!");
    loadAlertas(); // Recarregar lista
  } catch (error) {
    console.error("Erro no fluxo de geração de O.S:", error);
    alert("Falha ao processar solicitação.");
  }
};

const resolverAlerta = async (alerta) => {
  try {
    const response = await api.patch(`alertas/${alerta.id}/`, {
      status: 'resolvido'
    });
    const index = alertas.value.findIndex(a => a.id === alerta.id);
    if (index !== -1) {
      alertas.value[index] = response.data;
    }
  } catch (error) {
    console.error("Erro ao resolver alerta:", error);
  }
};

const getNivelClass = (nivel) => {
  if (nivel === 'critico') return 'badge-critico';
  if (nivel === 'medio') return 'badge-medio';
  return 'badge-baixo';
};

const getStatusLabel = (status) => {
  if (status === 'ativo') return 'Pendente';
  if (status === 'resolvido') return 'Resolvido';
  return status;
};

const formatData = (isoString) => {
  if (!isoString) return '-';
  const date = new Date(isoString);
  return date.toLocaleString('pt-BR', { 
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit'
  });
};

onMounted(() => {
  loadAlertas();
});
</script>

<template>
  <div class="alertas-view">
    <div class="page-header">
      <div class="title-group">
        <h2>Central de Alertas</h2>
        <p>Gerencie ocorrências e anomalias detectadas pelos sensores</p>
      </div>
      <div class="header-actions">
        <button class="action-btn-outline" @click="loadAlertas" :disabled="isLoading">
          <svg class="icon icon-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          Atualizar
        </button>
      </div>
    </div>

    <div v-if="isLoading && alertas.length === 0" class="loading-state glass-panel">
      <div class="loader-spinner"></div>
      <p>Consultando banco de alertas...</p>
    </div>

    <div v-else-if="alertas.length === 0" class="empty-state glass-panel">
      <svg class="icon-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
      <h3>Nenhum alerta ativo</h3>
      <p>Parabéns! No momento não há anomalias pendentes de resolução.</p>
    </div>

    <div v-else class="table-container glass-panel">
      <table class="alertas-table">
        <thead>
          <tr>
            <th>Data/Hora</th>
            <th>Equipamento</th>
            <th>Tipo / Descrição</th>
            <th>Nível</th>
            <th>Status</th>
            <th class="text-right">Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="alerta in alertas" :key="alerta.id" :class="{ 'row-resolvido': alerta.status === 'resolvido' }">
            <td class="font-mono">{{ formatData(alerta.data_alerta) }}</td>
            <td>
              <span class="eq-name">{{ alerta.equipamento && alerta.equipamento.nome ? alerta.equipamento.nome : `Eq. #${alerta.equipamento}` }}</span>
            </td>
            <td>
              <div class="tipo-cell">
                <span class="tipo-label">{{ alerta.tipo_alerta }}</span>
                <span class="tipo-desc">{{ alerta.descricao }}</span>
              </div>
            </td>
            <td>
              <span class="nivel-badge" :class="getNivelClass(alerta.nivel)">
                {{ alerta.nivel.toUpperCase() }}
              </span>
            </td>
            <td>
              <span class="status-marker" :class="alerta.status">
                {{ getStatusLabel(alerta.status) }}
              </span>
            </td>
            <td class="text-right">
              <div class="action-flex" v-if="alerta.status === 'ativo'">
                <button class="os-quick-btn" @click="abrirModalOS(alerta)" title="Abrir O.S">
                  <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path></svg>
                  O.S
                </button>
                <button class="resolve-btn-icon" @click="resolverAlerta(alerta)" title="Resolver">
                  <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                </button>
              </div>
              <span v-else class="check-icon">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Gerar O.S -->
    <transition name="fade">
      <div class="modal-overlay" v-if="isOSModalOpen">
        <div class="modal-content glass-panel">
          <div class="modal-header">
            <h3>Converter Alerta em O.S</h3>
            <button class="close-btn" @click="isOSModalOpen = false">×</button>
          </div>
          <form @submit.prevent="criarOSEMarcarResolvido" class="modal-form">
             <div class="form-group">
                <label>Título da Manutenção</label>
                <input v-model="osData.titulo" type="text" required />
             </div>
             <div class="form-group">
                <label>Descrição do Problema</label>
                <textarea v-model="osData.descricao" rows="3"></textarea>
             </div>
             <div class="form-group">
                <label>Prioridade Sugerida</label>
                <select v-model="osData.prioridade">
                   <option value="baixa">Baixa</option>
                   <option value="media">Média</option>
                   <option value="alta">Alta</option>
                   <option value="urgente">Urgente</option>
                </select>
             </div>
             <div class="modal-actions">
                <button type="button" class="btn-cancel" @click="isOSModalOpen = false">Cancelar</button>
                <button type="submit" class="premium-btn">Confirmar e Abrir O.S</button>
             </div>
          </form>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 2rem;
}

.title-group h2 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}

.title-group p {
  color: var(--color-text-muted);
}

.action-btn-outline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font-weight: 500;
  transition: all var(--transition-fast);
}

.action-btn-outline:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: var(--color-text-muted);
}

.icon-sm {
  width: 18px;
  height: 18px;
}

/* Tabela */
.table-container {
  overflow: hidden;
  border-radius: var(--radius-lg);
}

.alertas-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
}

.alertas-table th {
  padding: 1.25rem 1rem;
  background: rgba(15, 23, 42, 0.4);
  color: var(--color-text-muted);
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 700;
  border-bottom: 1px solid var(--color-border);
}

.alertas-table td {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  vertical-align: middle;
}

.alertas-table tr:hover td {
  background: rgba(255, 255, 255, 0.01);
}

.row-resolvido td {
  opacity: 0.6;
}

.font-mono {
  font-family: monospace;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.eq-name {
  font-weight: 600;
}

.tipo-cell {
  display: flex;
  flex-direction: column;
}

.tipo-label {
  font-weight: 600;
  margin-bottom: 0.1rem;
}

.tipo-desc {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.text-right { text-align: right; }

.action-flex {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.os-quick-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.5rem 0.8rem;
  background: rgba(59, 130, 246, 0.1);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: var(--radius-md);
  font-size: 0.75rem;
  font-weight: 700;
  transition: all 0.2s;
}

.os-quick-btn:hover { background: #3b82f6; color: white; }

.resolve-btn-icon {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.resolve-btn-icon:hover { background: #10b981; color: white; }

/* Badges de Nível */
.nivel-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
}

.badge-critico {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.badge-medio {
  background: rgba(245, 158, 11, 0.15);
  color: #fbbf24;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.badge-baixo {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

/* Status markers */
.status-marker {
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.status-marker::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-marker.ativo::before { background-color: #ef4444; box-shadow: 0 0 6px #ef4444; }
.status-marker.resolvido::before { background-color: #10b981; }

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 100%;
  max-width: 500px;
  padding: 2.5rem;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.close-btn { font-size: 2rem; color: var(--color-text-muted); }

.modal-form { display: flex; flex-direction: column; gap: 1.5rem; }

.form-group { display: flex; flex-direction: column; gap: 0.6rem; }

label { font-size: 0.8rem; color: var(--color-text-muted); font-weight: 500; }

input, select, textarea {
  padding: 0.85rem;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: white;
  width: 100%;
  font-family: inherit;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
}

.btn-cancel { color: var(--color-text-muted); }

.check-icon {
  color: #10b981;
}

.check-icon .icon {
  width: 24px;
  height: 24px;
}

/* Loading state */
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  color: var(--color-text-muted);
}

.loader-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-radius: 50%;
  border-top-color: var(--color-primary);
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin { 100% { transform: rotate(360deg); } }

.icon-lg {
  width: 48px;
  height: 48px;
  margin-bottom: 1rem;
  opacity: 0.6;
}
</style>
