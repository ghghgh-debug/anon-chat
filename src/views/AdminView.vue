<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { adminApi, userApi } from '../api'
import { t } from '../services/i18n'

const router = useRouter()
const isAdmin = ref(false)
const stats = ref<any>(null)
const referrals = ref<any[]>([])
const loading = ref(true)

const refCode = ref('')
const refCodeGenerated = ref('')

onMounted(async () => {
  try {
    const user = await userApi.getMe()
    if (!user.is_admin) {
      router.push('/')
      return
    }
    isAdmin.value = true
    
    await loadData()
  } catch (e) {
    console.error(e)
    router.push('/')
  } finally {
    loading.value = false
  }
})

async function loadData() {
  stats.value = await adminApi.getStats()
  const res = await adminApi.getReferrals()
  referrals.value = res.referrals || []
}

async function generateRef() {
  try {
    const res = await adminApi.createReferral(refCode.value || undefined)
    refCodeGenerated.value = res.code
    refCode.value = ''
    await loadData()
  } catch (e) {
    console.error(e)
  }
}
</script>

<template>
  <div class="container fade-in" v-if="isAdmin">
    <div class="header">
      <button class="btn-ghost" @click="router.push('/')">{{ t('back') }}</button>
      <h2 style="color: var(--accent-red)">{{ t('root_access') }}</h2>
    </div>

    <div v-if="loading" class="center"><div class="cyber-spinner"></div></div>

    <div v-else class="content">
      <!-- Stats -->
      <div class="stats-grid slide-up">
        <div class="glass-card stat-box">
          <div class="s-val">{{ stats.total_users }}</div>
          <div class="s-lbl">{{ t('total_users') }}</div>
        </div>
        <div class="glass-card stat-box">
          <div class="s-val">{{ referrals.length }}</div>
          <div class="s-lbl">{{ t('total_referrals') }}</div>
        </div>
        <div class="glass-card stat-box">
          <div class="s-val">{{ stats.active_chats }}</div>
          <div class="s-lbl">{{ t('active_conns') }}</div>
        </div>
        <div class="glass-card stat-box">
          <div class="s-val" style="color: var(--accent-red)">{{ stats.total_reports }}</div>
          <div class="s-lbl">{{ t('reports') }}</div>
        </div>
      </div>

      <!-- Quick Actions -->
      <h3 class="section-title slide-up">{{ t('command_module') }}</h3>
      
      <div class="glass-card action-card slide-up">
        <h4>{{ t('generate_referral_code_title') }}</h4>
        <div class="input-row">
          <input 
            v-model="refCode" 
            type="text" 
            class="input-neon cyber-input" 
            :placeholder="t('custom_code_opt')" 
          />
          <button class="btn-neon" style="background: var(--accent-red)" @click="generateRef">GEN</button>
        </div>
        <div v-if="refCodeGenerated" class="res-code neon-text">
          SUCCESS: {{ refCodeGenerated }}
        </div>
      </div>

      <!-- Referrals Table -->
      <div class="glass-card action-card slide-up" style="margin-top: 24px;">
        <h4>{{ t('active_referrals') }}</h4>
        <div class="ref-list" v-if="referrals.length > 0">
          <div v-for="refItem in referrals" :key="refItem.id" class="ref-item">
            <span class="ref-code neon-text">{{ refItem.code }}</span>
            <span class="ref-count">{{ t('uses_count') }}: {{ refItem.uses_count }}</span>
          </div>
        </div>
        <p v-else class="empty-text">{{ t('no_referrals_found') }}</p>
      </div>
      
      <div class="warning-box slide-up" style="margin-top: 24px;">
        <strong>WARNING:</strong> Full moderation features (banning, viewing reports, log streams) are restricted to the Desktop Admin Interface. This terminal provides basic telemetry only.
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  padding: 24px;
  max-width: 600px;
  margin: 0 auto;
}

.header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
}

.header h2 {
  font-family: monospace;
  font-weight: 800;
  letter-spacing: 2px;
  margin: 0;
  text-shadow: 0 0 10px rgba(244, 63, 94, 0.4);
}

.center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.cyber-spinner {
  width: 40px; height: 40px;
  border: 2px solid transparent;
  border-top-color: var(--accent-red);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 32px;
}

.stat-box {
  padding: 20px;
  text-align: center;
  border-color: rgba(244, 63, 94, 0.2);
}

.s-val {
  font-size: 28px;
  font-weight: 900;
  font-family: monospace;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.s-lbl {
  font-size: 11px;
  font-family: monospace;
  color: var(--text-secondary);
  letter-spacing: 1px;
}

.section-title {
  font-family: monospace;
  font-size: 16px;
  margin-bottom: 16px;
  color: var(--accent-red);
}

.action-card {
  padding: 20px;
  margin-bottom: 24px;
  border-color: rgba(244, 63, 94, 0.2);
}

.action-card h4 {
  font-family: monospace;
  font-size: 12px;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.input-row {
  display: flex;
  gap: 12px;
}

.cyber-input {
  font-family: monospace;
  flex: 1;
}

.res-code {
  margin-top: 12px;
  font-family: monospace;
  font-size: 14px;
  padding: 10px;
  background: rgba(168, 85, 247, 0.1);
  border-radius: 8px;
}

.ref-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 250px;
  overflow-y: auto;
}

.ref-item {
  display: flex;
  justify-content: space-between;
  padding: 10px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  font-family: monospace;
}

.ref-code {
  font-weight: bold;
}

.ref-count {
  color: var(--text-secondary);
}

.empty-text {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-muted);
}

.warning-box {
  padding: 16px;
  background: rgba(244, 63, 94, 0.1);
  border: 1px dashed var(--accent-red);
  border-radius: 8px;
  font-family: monospace;
  font-size: 12px;
  color: var(--accent-red);
  line-height: 1.5;
}
</style>
