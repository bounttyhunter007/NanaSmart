<script setup>
import { ref, onMounted } from 'vue';
import api from '../services/api';

const equipamentos = ref([]);
const isLoading = ref(true);
const isModalOpen = ref(false);
const isAdmin = ref(false);

const novoEquipamento = ref({
  nome: '',
  tipo: '',
  fabricante: '',
  numero_serie: '',
  status: 'ativo',
  empresa: 1
});

const loadProfile = async () => {
  try {
    const res = await api.get('auth/me/');
    if (res.data.tipo_usuario === 'admin') {
      isAdmin.value = true;
    }
  } catch(e) {}
};

const loadEquipamentos = async () => {
  isLoading.value = true;
  try {
    const response = await api.get('equipamentos/');
    equipamentos.value = response.data.results || response.data;
  } catch (error) {
    console.error("Erro ao puxar equipamentos", error);
  } finally {
    isLoading.value = false;
  }
};

const criarEquipamento = async () => {
  try {
    const response = await api.post('equipamentos/', novoEquipamento.value);
    equipamentos.value.push(response.data);
    isModalOpen.value = false;
    novoEquipamento.value = { nome: '', tipo: '', fabricante: '', numero_serie: '', status: 'ativo', empresa: 1 };
  } catch (error) {
    console.error("Erro ao criar equipamento:", error.response?.data || error);
    alert('Erro ao criar equipamento. Verifique se o nº de série não é duplicado.');
  }
};

onMounted(async () => {
  await loadProfile();
  loadEquipamentos();
});

const getStatusClass = (status) => {
  if (status === 'ativo') return 'status-badge success';
  if (status === 'manutencao') return 'status-badge warning';
  return 'status-badge danger';
};
</script>

<template>
  <div class="ativos-view">
    <div class="page-header">
      <div class="title-group">
        <h2>Gestão de Ativos</h2>
        <p>Monitoramento e acompanhamento do parque de máquinas</p>
      </div>
      <button v-if="isAdmin" class="premium-btn" @click="isModalOpen = true">
        <svg class="icon icon-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
        Cadastrar Equipamento
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="loading-state glass-panel">
      <div class="loader-spinner"></div>
      <p>Carregando equipamentos...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="equipamentos.length === 0" class="empty-state glass-panel">
      <svg class="icon-lg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11v9h-5a2 2 0 01-2-2v-4a2 2 0 012-2h5m-11 0V4h5a2 2 0 012 2v4a2 2 0 01-2 2H8m0 0V4m0 9v9m-4 0h4m4-18h4"></path></svg>
      <h3>Nenhum equipamento monitorado</h3>
      <p>Você ainda não possui equipamentos cadastrados no sistema.</p>
    </div>

    <!-- Listagem -->
    <div v-else class="ativos-grid">
      <div class="ativo-card glass-panel" v-for="eq in equipamentos" :key="eq.id">
        <div class="card-header">
          <div class="icon-box">
             <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
          </div>
          <span :class="getStatusClass(eq.status)">
            {{ eq.status.charAt(0).toUpperCase() + eq.status.slice(1) }}
          </span>
        </div>
        
        <div class="card-body">
          <h3 class="eq-name">{{ eq.nome }}</h3>
          <p class="eq-tipo">{{ eq.tipo || 'Sem classificação' }}</p>
          
          <div class="eq-details">
            <div class="detail-row">
              <span class="label">S/N:</span>
              <span class="value">{{ eq.numero_serie }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Fabricante:</span>
              <span class="value">{{ eq.fabricante || '-' }}</span>
            </div>
          </div>
        </div>
        
        <div class="card-footer">
          <button class="action-btn">Telemetria</button>
          <button class="action-btn">Histórico</button>
        </div>
      </div>
    </div>

    <!-- Modal Novo Equipamento -->
    <transition name="fade">
      <div class="modal-overlay" v-if="isModalOpen">
        <div class="modal-content glass-panel">
          <div class="modal-header">
            <h3>Novo Equipamento</h3>
            <button class="close-btn" @click="isModalOpen = false">×</button>
          </div>
          
          <form @submit.prevent="criarEquipamento" class="modal-form">
            <div class="form-group">
              <label>Nome do Equipamento *</label>
              <input v-model="novoEquipamento.nome" type="text" required placeholder="Ex: Bomba de Água Principal" />
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label>Número de Série *</label>
                <input v-model="novoEquipamento.numero_serie" type="text" required placeholder="Ex: SN-12345" />
              </div>
              <div class="form-group">
                <label>Tipo</label>
                <input v-model="novoEquipamento.tipo" type="text" placeholder="Ex: Motor" />
              </div>
            </div>

            <div class="form-row">
              <div class="form-group">
                <label>Fabricante</label>
                <input v-model="novoEquipamento.fabricante" type="text" />
              </div>
              <div class="form-group">
                <label>Status Inicial</label>
                <select v-model="novoEquipamento.status">
                  <option value="ativo">Ativo</option>
                  <option value="manutencao">Em Manutenção</option>
                  <option value="inativo">Inativo</option>
                </select>
              </div>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-cancel" @click="isModalOpen = false">Cancelar</button>
              <button type="submit" class="premium-btn">Salvar Equipamento</button>
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

.icon-sm {
  width: 18px;
  height: 18px;
}

/* Loading & Empty */
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;
  color: var(--color-text-muted);
}

.icon-lg {
  width: 48px;
  height: 48px;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.loader-spinner {
  width: 30px;
  height: 30px;
  border: 3px solid rgba(59, 130, 246, 0.2);
  border-radius: 50%;
  border-top-color: var(--color-primary);
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin { 100% { transform: rotate(360deg); } }

/* Grid de Ativos */
.ativos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.ativo-card {
  display: flex;
  flex-direction: column;
  padding: 1.25rem;
  transition: transform 0.2s, box-shadow 0.2s;
}

.ativo-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
  border-color: rgba(59, 130, 246, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.icon-box {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  background: rgba(59, 130, 246, 0.1);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-box .icon {
  width: 22px;
  height: 22px;
}

.status-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-full);
}

.status-badge.success { background: rgba(16, 185, 129, 0.1); color: #34d399; }
.status-badge.warning { background: rgba(245, 158, 11, 0.1); color: #fbbf24; }
.status-badge.danger { background: rgba(239, 68, 68, 0.1); color: #f87171; }

.card-body {
  flex: 1;
  margin-bottom: 1.5rem;
}

.eq-name {
  font-size: 1.15rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

.eq-tipo {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-bottom: 1rem;
}

.eq-details {
  background: rgba(15, 23, 42, 0.5);
  padding: 0.75rem;
  border-radius: var(--radius-md);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  margin-bottom: 0.25rem;
}
.detail-row:last-child { margin-bottom: 0; }

.detail-row .label { color: var(--color-text-muted); }
.detail-row .value { font-weight: 500; }

.card-footer {
  display: flex;
  gap: 0.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 1rem;
}

.action-btn {
  flex: 1;
  padding: 0.5rem;
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.05);
  color: var(--color-text);
  border: 1px solid transparent;
  transition: all var(--transition-fast);
}

.action-btn:hover {
  background: rgba(59, 130, 246, 0.1);
  color: var(--color-primary);
  border-color: rgba(59, 130, 246, 0.3);
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal-content {
  width: 100%;
  max-width: 500px;
  padding: 2rem;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.modal-header h3 { font-size: 1.25rem; }

.close-btn {
  font-size: 1.5rem;
  color: var(--color-text-muted);
  line-height: 1;
}

.close-btn:hover { color: var(--color-text); }

.modal-form { display: flex; flex-direction: column; gap: 1.25rem; }

.form-group { display: flex; flex-direction: column; gap: 0.5rem; }

.form-row { display: flex; gap: 1rem; }
.form-row .form-group { flex: 1; }

label { font-size: 0.85rem; color: var(--color-text-muted); }

input, select {
  padding: 0.75rem;
  background-color: rgba(15, 23, 42, 0.5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  outline: none;
  transition: border-color 0.2s;
}

input:focus, select:focus { border-color: var(--color-primary); }

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.btn-cancel {
  padding: 0.5rem 1rem;
  color: var(--color-text-muted);
  border-radius: var(--radius-md);
  transition: background 0.2s;
}
.btn-cancel:hover { background: rgba(255, 255, 255, 0.05); color: var(--color-text); }
</style>
