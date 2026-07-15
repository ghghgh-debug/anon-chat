<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { userApi } from '../api'

const router = useRouter()
const user = ref<any>(null)
const loading = ref(true)
const error = ref('')

const isEditing = ref(false)
const editData = ref({
  nickname: '',
  age: 18,
  bio: '',
})

onMounted(async () => {
  await loadUser()
})

async function loadUser() {
  try {
    user.value = await userApi.getMe()
    editData.value = {
      nickname: user.value.nickname,
      age: user.value.age,
      bio: user.value.bio || '',
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  loading.value = true
  try {
    await userApi.updateProfile(editData.value)
    isEditing.value = false
    await loadUser()
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}
</script>

<template>
  <div class="container fade-in">
    <div class="header">
      <button class="btn-ghost" @click="router.push('/')">&lt; BACK</button>
      <h2 class="neon-text">SYS_PROFILE</h2>
    </div>

    <div v-if="loading && !user" class="center">
      <div class="cyber-spinner"></div>
    </div>

    <div v-else-if="user" class="profile-content">
      <!-- Avatar Section -->
      <div class="avatar-section glass-card neon-border">
        <div class="avatar">
          <div class="avatar-placeholder">{{ user.nickname[0]?.toUpperCase() }}</div>
          <div v-if="user.is_premium" class="badge-premium premium-float">⭐ VIP</div>
        </div>
        <div class="rep-bar">
          <div class="rep-fill" :style="{ width: `${user.reputation_percent}%`, background: user.reputation_percent >= 50 ? 'var(--accent-green)' : 'var(--accent-red)' }"></div>
        </div>
        <div class="rep-text">REP_SCORE: {{ user.reputation_percent }}%</div>
      </div>

      <!-- Stats Grid -->
      <div class="stats-grid">
        <div class="glass-card stat-box">
          <div class="stat-val neon-text">{{ user.likes }}</div>
          <div class="stat-label">LIKES</div>
        </div>
        <div class="glass-card stat-box">
          <div class="stat-val" style="color: var(--accent-red)">{{ user.dislikes }}</div>
          <div class="stat-label">DISLIKES</div>
        </div>
        <div class="glass-card stat-box" style="grid-column: span 2">
          <div class="stat-val neon-text">{{ formatTime(user.total_chat_seconds) }}</div>
          <div class="stat-label">UPTIME</div>
        </div>
      </div>

      <!-- Info / Edit Section -->
      <div class="glass-card info-card">
        <div class="card-header">
          <h3 class="neon-text">USER_DATA</h3>
          <button class="btn-ghost small" @click="isEditing = !isEditing">
            {{ isEditing ? 'CANCEL' : 'EDIT' }}
          </button>
        </div>

        <div v-if="!isEditing" class="info-view">
          <div class="i-row"><span>ALIAS:</span> <span class="neon-text">{{ user.nickname }}</span></div>
          <div class="i-row"><span>AGE:</span> <span class="neon-text">{{ user.age }}</span></div>
          <div class="i-row"><span>SEX:</span> <span class="neon-text">{{ user.gender.toUpperCase() }}</span></div>
          <div class="i-row"><span>BIO:</span> <span class="neon-text">{{ user.bio || 'null' }}</span></div>
        </div>

        <div v-else class="edit-view slide-up">
          <div class="input-group">
            <label>ALIAS</label>
            <input v-model="editData.nickname" type="text" class="input-neon cyber-input" />
          </div>
          <div class="input-group">
            <label>AGE</label>
            <input v-model.number="editData.age" type="number" class="input-neon cyber-input" />
          </div>
          <div class="input-group">
            <label>BIO</label>
            <textarea v-model="editData.bio" class="input-neon cyber-input" rows="3"></textarea>
          </div>
          
          <p v-if="error" style="color: var(--accent-red)">ERR: {{ error }}</p>
          <button class="btn-neon full-w" @click="saveProfile" :disabled="loading">SAVE_DATA</button>
        </div>
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
}

.center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.cyber-spinner {
  width: 40px; height: 40px;
  border: 2px solid transparent;
  border-top-color: var(--neon-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 20px;
  margin-bottom: 24px;
}

.avatar {
  position: relative;
  width: 80px;
  height: 80px;
  margin-bottom: 20px;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--gradient-card);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  font-weight: 900;
  color: var(--neon-bright);
  border: 2px solid var(--neon-glow);
}

.premium-float {
  position: absolute;
  bottom: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--bg-deep);
}

.rep-bar {
  width: 100%;
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.rep-fill {
  height: 100%;
  transition: width 0.5s ease;
}

.rep-text {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
}

.stat-box {
  padding: 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-val {
  font-size: 24px;
  font-weight: 900;
  font-family: monospace;
}

.stat-label {
  font-size: 10px;
  font-family: monospace;
  color: var(--text-muted);
  letter-spacing: 1px;
}

.info-card {
  padding: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h3 {
  font-family: monospace;
  font-size: 16px;
  margin: 0;
}

.small {
  padding: 4px 10px;
  font-size: 11px;
}

.info-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.i-row {
  display: flex;
  justify-content: space-between;
  font-family: monospace;
  font-size: 14px;
  border-bottom: 1px dashed var(--border-subtle);
  padding-bottom: 8px;
}

.edit-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-group label {
  display: block;
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.cyber-input {
  font-family: monospace;
}

.full-w { width: 100%; margin-top: 16px; }
</style>
