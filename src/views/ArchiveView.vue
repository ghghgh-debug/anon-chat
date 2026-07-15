<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { chatApi } from '../api'

const router = useRouter()
const archive = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await chatApi.getArchive()
    archive.value = res.archive
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

function formatDateTime(iso: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.toLocaleDateString()} ${d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`
}
</script>

<template>
  <div class="container fade-in">
    <div class="header">
      <button class="btn-ghost" @click="router.push('/')">&lt; BACK</button>
      <h2 class="neon-text">CHAT_ARCHIVE</h2>
    </div>

    <div v-if="loading" class="center"><div class="cyber-spinner"></div></div>

    <div v-else-if="archive.length === 0" class="center empty">
      <p class="neon-text">NO_RECORDS_FOUND</p>
    </div>

    <div v-else class="archive-list">
      <div v-for="chat in archive" :key="chat.chat_id" class="glass-card archive-item slide-up">
        <div class="a-header">
          <span class="a-partner neon-text">
            {{ chat.partner.chosen_emoji || '' }} {{ chat.partner.nickname }}
          </span>
          <span v-if="chat.partner.is_premium" class="badge-premium">VIP</span>
        </div>

        <div class="a-details">
          <div class="d-row"><span>START:</span> <span>{{ formatDateTime(chat.started_at) }}</span></div>
          <div class="d-row"><span>END:</span> <span>{{ chat.is_active ? 'ACTIVE' : formatDateTime(chat.ended_at) }}</span></div>
          <div v-if="!chat.is_active" class="d-row"><span>REASON:</span> <span>{{ chat.ended_reason }}</span></div>
        </div>

        <button class="btn-ghost full-w mt-2" @click="router.push(`/chat/${chat.chat_id}`)">
          {{ chat.is_active ? 'RECONNECT' : 'VIEW_TRANSCRIPT' }}
        </button>
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

.empty {
  opacity: 0.5;
  font-family: monospace;
}

.cyber-spinner {
  width: 40px; height: 40px;
  border: 2px solid transparent;
  border-top-color: var(--neon-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.archive-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.archive-item {
  padding: 16px;
}

.a-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
}

.a-partner {
  font-size: 16px;
  font-weight: 800;
  font-family: monospace;
}

.a-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
}

.d-row {
  display: flex;
  justify-content: space-between;
}

.full-w { width: 100%; }
.mt-2 { margin-top: 12px; }
</style>
