<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { userApi, chatApi } from '../api'

const router = useRouter()
const user = ref<any>(null)
const onlineCount = ref(0)
const loading = ref(true)
const error = ref('')

let heartbeatInterval: number | null = null

onMounted(async () => {
  try {
    user.value = await userApi.getMe()
    const online = await chatApi.getOnlineCount()
    onlineCount.value = online.online

    // Heartbeat every 20 seconds
    heartbeatInterval = window.setInterval(async () => {
      try {
        await chatApi.heartbeat()
        const o = await chatApi.getOnlineCount()
        onlineCount.value = o.online
      } catch {}
    }, 20000)
  } catch (e: any) {
    if (e.message?.includes('not found') || e.message?.includes('onboarding')) {
      router.push('/onboarding')
      return
    }
    error.value = e.message
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (heartbeatInterval) clearInterval(heartbeatInterval)
})

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}ч ${m}мин`
  return `${m}мин`
}
</script>

<template>
  <div class="container fade-in">
    <!-- Loading -->
    <div v-if="loading" class="center-screen">
      <div class="cyber-spinner"></div>
      <p class="neon-text">ЗАГРУЗКА...</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="center-screen">
      <p style="color: var(--accent-red)">{{ error }}</p>
      <button class="btn-neon" @click="router.push('/onboarding')">ИНИЦИАЛИЗАЦИЯ</button>
    </div>

    <!-- Main Content -->
    <div v-else-if="user" class="content">
      <!-- Header -->
      <div class="header">
        <div class="greeting">
          <span v-if="user.chosen_emoji" class="emoji-badge">{{ user.chosen_emoji }}</span>
          <h2>{{ user.is_admin ? 'SYSADMIN 👑' : `ПРИВЕТ, ${user.nickname.toUpperCase()}` }}</h2>
        </div>
        <div class="badge-online">
          {{ onlineCount }} ONLINE
        </div>
      </div>

      <!-- User Card -->
      <div class="glass-card user-card" @click="router.push('/profile')">
        <div class="avatar-wrapper neon-border">
          <img v-if="user.avatar_url" :src="user.avatar_url" alt="Avatar" />
          <div v-else class="avatar-placeholder">{{ user.nickname[0]?.toUpperCase() }}</div>
          <span v-if="user.is_premium" class="premium-badge badge-premium">⭐ VIP</span>
        </div>
        <div class="user-info">
          <div class="nickname neon-text">
            <span v-if="user.chosen_emoji">{{ user.chosen_emoji }} </span>
            {{ user.nickname }}
          </div>
          <div class="stats-row">
            <span class="stat">👍 {{ user.likes }}</span>
            <span class="stat">👎 {{ user.dislikes }}</span>
            <span class="stat reputation" :style="{ color: user.reputation_percent >= 70 ? 'var(--accent-green)' : 'var(--accent-red)' }">
              REP: {{ user.reputation_percent }}%
            </span>
          </div>
          <div class="time-stat">UPTIME: {{ formatTime(user.total_chat_seconds) }}</div>
        </div>
        <span class="chevron">›</span>
      </div>

      <!-- Main Action -->
      <button class="btn-neon search-button slide-up" @click="router.push('/search')">
        <span class="search-icon">🔍</span>
        СТАРТ ПОИСКА
      </button>

      <!-- Menu Grid -->
      <div class="menu-grid slide-up" style="animation-delay: 0.1s;">
        <div class="glass-card menu-item" @click="router.push('/archive')">
          <span class="menu-icon neon-text">💬</span>
          <span>АРХИВ</span>
        </div>
        <div class="glass-card menu-item" @click="router.push('/leaderboard')">
          <span class="menu-icon neon-text">🏆</span>
          <span>ТОП-100</span>
        </div>
        <div class="glass-card menu-item" @click="router.push('/premium')">
          <span class="menu-icon neon-text">👑</span>
          <span>PREMIUM</span>
        </div>
        <div class="glass-card menu-item" @click="router.push('/profile')">
          <span class="menu-icon neon-text">👤</span>
          <span>ПРОФИЛЬ</span>
        </div>
      </div>

      <!-- Admin Panel Link -->
      <button v-if="user.is_admin" class="btn-ghost admin-link slide-up" style="animation-delay: 0.2s;" @click="router.push('/admin')">
        <span>🛡</span> ROOT ACCESS
      </button>
    </div>
  </div>
</template>

<style scoped>
.container {
  padding: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.center-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
  gap: 24px;
}

.cyber-spinner {
  width: 50px;
  height: 50px;
  border: 2px solid transparent;
  border-top-color: var(--neon-primary);
  border-bottom-color: var(--neon-bright);
  border-radius: 50%;
  animation: spin 1s linear infinite, neonPulse 2s infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.greeting h2 {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 1px;
  margin: 0;
  text-shadow: 0 0 10px rgba(255,255,255,0.3);
}

.user-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  margin-bottom: 24px;
  cursor: pointer;
}

.avatar-wrapper {
  position: relative;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-deep);
}

.avatar-wrapper img, .avatar-placeholder {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-card);
  font-size: 24px;
  font-weight: 800;
  color: var(--neon-bright);
}

.premium-badge {
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
}

.user-info {
  flex: 1;
}

.nickname {
  font-size: 18px;
  font-weight: 800;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}

.stats-row {
  display: flex;
  gap: 12px;
  font-size: 13px;
  font-family: monospace;
  margin-bottom: 4px;
}

.stat {
  background: rgba(255,255,255,0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.time-stat {
  font-size: 11px;
  font-family: monospace;
  color: var(--text-muted);
}

.chevron {
  font-size: 28px;
  color: var(--neon-glow);
}

.search-button {
  width: 100%;
  padding: 20px;
  font-size: 16px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.search-icon {
  font-size: 20px;
}

.menu-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.menu-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 24px 16px;
  cursor: pointer;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 13px;
}

.menu-icon {
  font-size: 32px;
}

.admin-link {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--accent-red);
  border-color: rgba(244, 63, 94, 0.3);
}

.admin-link:hover {
  background: rgba(244, 63, 94, 0.1);
  box-shadow: 0 0 15px rgba(244, 63, 94, 0.2);
}
</style>
