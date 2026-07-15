<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { userApi } from '../api'

const router = useRouter()
const leaderboard = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await userApi.getLeaderboard()
    leaderboard.value = res.leaderboard
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

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
      <h2 class="neon-text">TOP_100_NODES</h2>
    </div>

    <div v-if="loading" class="center"><div class="cyber-spinner"></div></div>

    <div v-else class="lb-list">
      <div
        v-for="(u, index) in leaderboard"
        :key="index"
        class="glass-card lb-item slide-up"
        :style="{ animationDelay: `${index * 0.05}s` }"
      >
        <div class="rank" :class="{ 'top-3': index < 3 }">#{{ u.rank }}</div>

        <div class="lb-info">
          <div class="lb-name">
            <span v-if="u.chosen_emoji">{{ u.chosen_emoji }} </span>
            <span class="neon-text">{{ u.nickname }}</span>
            <span v-if="u.is_premium" class="badge-premium ml-2">VIP</span>
          </div>
          <div class="lb-stats">
            <span class="rep" :class="{ bad: u.reputation_percent < 50 }">REP: {{ u.reputation_percent }}%</span>
            <span class="time">UPTIME: {{ formatTime(u.total_chat_seconds) }}</span>
          </div>
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

.lb-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.lb-item {
  display: flex;
  align-items: center;
  padding: 16px;
  gap: 16px;
}

.rank {
  font-family: monospace;
  font-size: 20px;
  font-weight: 900;
  color: var(--text-muted);
  width: 40px;
  text-align: center;
}

.rank.top-3 {
  color: var(--accent-gold);
  text-shadow: 0 0 10px rgba(251, 191, 36, 0.5);
}

.lb-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lb-name {
  font-size: 16px;
  font-weight: 700;
  font-family: monospace;
}

.ml-2 { margin-left: 8px; }

.lb-stats {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-family: monospace;
  color: var(--text-secondary);
}

.rep { color: var(--accent-green); }
.rep.bad { color: var(--accent-red); }
</style>
