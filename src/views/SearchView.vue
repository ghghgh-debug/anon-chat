<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { chatApi, userApi } from '../api'
import { connectCentrifugo, subscribeToChannel, disconnectCentrifugo, type ChatMessage } from '../services/centrifugo'
import { t, currentLang } from '../services/i18n'

const router = useRouter()
const status = ref<'filters' | 'searching' | 'matched'>('filters')
const loading = ref(false)
const error = ref('')
const user = ref<any>(null)

const findGender = ref('any')
const ageFrom = ref(14)
const ageTo = ref(99)
const vipOnly = ref(false)

const ageCategory = ref<'any' | 'teen' | 'adult' | 'custom'>('any')

function selectAgeCategory(cat: 'any' | 'teen' | 'adult') {
  ageCategory.value = cat
  if (cat === 'teen') {
    ageFrom.value = 14
    ageTo.value = 18
  } else if (cat === 'adult') {
    ageFrom.value = 18
    ageTo.value = 99
  } else {
    ageFrom.value = 14
    ageTo.value = 99
  }
}

const selectedTopic = ref('topic_chat')
const chatLang = ref<string>('ru')

const topicsList = [
  { key: 'topic_chat', icon: '💬' },
  { key: 'topic_flirt', icon: '❤️' },
  { key: 'topic_photos', icon: '📷' },
  { key: 'topic_games', icon: '🎮' },
  { key: 'topic_life', icon: '🌿' },
  { key: 'topic_nsfw', icon: '🔥' },
]

let searchInterval: number | null = null
const searchCode = ref('')

onMounted(async () => {
  try {
    user.value = await userApi.getMe()
    // Default chat language to current app language
    chatLang.value = currentLang.value
  } catch (e: any) {
    error.value = e.message
  }
})

onUnmounted(() => {
  if (searchInterval) clearInterval(searchInterval)
  disconnectCentrifugo()
})

function generateCyberCode() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
  let code = ''
  for (let i=0; i<15; i++) {
    code += chars.charAt(Math.floor(Math.random() * chars.length))
    if ((i+1)%5===0 && i<14) code += ' '
  }
  return code
}

async function startSearch() {
  loading.value = true
  error.value = ''
  status.value = 'searching'

  searchInterval = window.setInterval(() => {
    searchCode.value = generateCyberCode()
  }, 100)

  try {
    const result = await chatApi.search({
      find_gender: findGender.value,
      age_from: ageFrom.value,
      age_to: ageTo.value,
      vip_only: vipOnly.value,
      topics: [selectedTopic.value], // send topic as topics list
      // Also pass chat_lang as part of custom filter options
      ...(chatLang.value ? { chat_lang: chatLang.value } : {})
    } as any)

    if (result.status === 'matched') {
      handleMatch(result.room_key, result.channel, result.token, result.chat_id)
    } else {
      const centrifuge = connectCentrifugo(result.token)
      subscribeToChannel(result.channel, result.token, (msg: ChatMessage) => {
        if (msg.event === 'matched') {
          handleMatch(msg.room_key!, msg.channel!, msg.token!)
        }
      })
    }
  } catch (e: any) {
    error.value = e.message
    status.value = 'filters'
    if (searchInterval) clearInterval(searchInterval)
  } finally {
    loading.value = false
  }
}

function handleMatch(roomKey: string, channel: string, token: string, chatId?: number) {
  status.value = 'matched'
  if (searchInterval) clearInterval(searchInterval)
  setTimeout(() => {
    router.push(`/chat/${chatId || roomKey}?channel=${channel}&token=${token}`)
  }, 1500)
}

async function cancelSearch() {
  try { await chatApi.cancelSearch() } catch {}
  if (searchInterval) clearInterval(searchInterval)
  disconnectCentrifugo()
  status.value = 'filters'
}
</script>

<template>
  <div class="container fade-in">
    <button v-if="status === 'filters'" class="btn-ghost back-btn" @click="router.push('/')">{{ t('back') }}</button>

    <!-- Filters -->
    <div v-if="status === 'filters'" class="section">
      <h2 class="neon-text title">{{ t('scan_parameters') }}</h2>

      <div class="glass-card config-panel">
        <!-- Topic Selection -->
        <div class="param-group">
          <label class="param-label">{{ t('select_topic').toUpperCase() }}</label>
          <div class="topics-grid">
            <button 
              v-for="topic in topicsList" 
              :key="topic.key"
              class="btn-ghost topic-select-btn"
              :class="{ active: selectedTopic === topic.key }"
              @click="selectedTopic = topic.key"
            >
              <span class="topic-icon">{{ topic.icon }}</span>
              <span>{{ t(topic.key) }}</span>
            </button>
          </div>
        </div>

        <!-- Chat Language -->
        <div class="param-group">
          <label class="param-label">{{ t('select_chat_lang').toUpperCase() }}</label>
          <div class="btn-group">
            <button class="btn-ghost" :class="{ active: chatLang === 'ru' }" @click="chatLang = 'ru'">RU</button>
            <button class="btn-ghost" :class="{ active: chatLang === 'en' }" @click="chatLang = 'en'">EN</button>
            <button class="btn-ghost" :class="{ active: chatLang === 'uz' }" @click="chatLang = 'uz'">UZ</button>
          </div>
        </div>

        <!-- Target Gender -->
        <div class="param-group">
          <label class="param-label">{{ t('target_gender') }}</label>
          <div class="btn-group">
            <button class="btn-ghost" :class="{ active: findGender === 'any' }" @click="findGender = 'any'">{{ t('any_gender') }}</button>
            <button 
              class="btn-ghost" 
              :class="{ active: findGender === 'male', locked: !user?.is_premium }" 
              @click="user?.is_premium ? findGender = 'male' : null"
            >{{ t('male') }} {{ !user?.is_premium ? '🔒' : '' }}</button>
            <button 
              class="btn-ghost" 
              :class="{ active: findGender === 'female', locked: !user?.is_premium }" 
              @click="user?.is_premium ? findGender = 'female' : null"
            >{{ t('female') }} {{ !user?.is_premium ? '🔒' : '' }}</button>
          </div>
          <p v-if="!user?.is_premium" class="premium-hint">{{ t('req_premium_license') }} <span class="neon-text" @click="router.push('/premium')">PREMIUM</span></p>
        </div>

        <!-- Target Age Group -->
        <div class="param-group">
          <label class="param-label">{{ t('target_age_group') }}</label>
          <div class="btn-group">
            <button 
              type="button"
              class="btn-ghost" 
              :class="{ active: ageCategory === 'any' }" 
              @click="selectAgeCategory('any')"
            >
              {{ t('age_group_any') }}
            </button>
            <button 
              type="button"
              class="btn-ghost" 
              :class="{ active: ageCategory === 'teen' }" 
              @click="selectAgeCategory('teen')"
            >
              {{ t('age_group_teen') }}
            </button>
            <button 
              type="button"
              class="btn-ghost" 
              :class="{ active: ageCategory === 'adult' }" 
              @click="selectAgeCategory('adult')"
            >
              {{ t('age_group_adult') }}
            </button>
          </div>
        </div>

        <!-- Age Range -->
        <div class="param-group">
          <label class="param-label">{{ t('age_range') }} [{{ ageFrom }} - {{ ageTo }}]</label>
          <div class="range-group">
            <input type="range" v-model.number="ageFrom" min="14" max="99" class="cyber-range" @input="ageCategory = 'custom'" />
            <input type="range" v-model.number="ageTo" min="14" max="99" class="cyber-range" @input="ageCategory = 'custom'" />
          </div>
        </div>

        <!-- VIP Protocol -->
        <div v-if="user?.is_premium" class="param-group">
          <label class="cyber-checkbox">
            <input type="checkbox" v-model="vipOnly" />
            <span class="checkmark neon-border"></span>
            <span class="label-text neon-text" style="color: var(--accent-gold);">{{ t('restrict_vip') }}</span>
          </label>
        </div>
      </div>

      <p v-if="error" class="error-msg">ERR: {{ error }}</p>

      <button class="btn-neon start-btn" @click="startSearch" :disabled="loading">
        {{ t('execute_scan') }}
      </button>
    </div>

    <!-- Searching -->
    <div v-if="status === 'searching'" class="section center-all">
      <div class="cyber-radar neon-border">
        <div class="scan-line"></div>
        <div class="data-stream">{{ searchCode }}</div>
      </div>
      <h2 class="neon-text pulse-text">{{ t('scanning_network') }}</h2>
      <button class="btn-ghost cancel-btn" @click="cancelSearch">{{ t('abort') }}</button>
    </div>

    <!-- Matched -->
    <div v-if="status === 'matched'" class="section center-all">
      <div class="match-icon neon-text">◆</div>
      <h2 class="neon-text">{{ t('connection_established') }}</h2>
      <p class="cyber-text">{{ t('routing') }}</p>
    </div>
  </div>
</template>

<style scoped>
.container {
  padding: 24px;
  max-width: 600px;
  margin: 0 auto;
  min-height: 100vh;
}

.back-btn {
  margin-bottom: 24px;
  font-family: monospace;
}

.title {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 2px;
  font-family: monospace;
  margin-bottom: 24px;
}

.config-panel {
  padding: 24px;
  margin-bottom: 32px;
}

.param-group {
  margin-bottom: 24px;
}

.param-group:last-child {
  margin-bottom: 0;
}

.param-label {
  display: block;
  font-family: monospace;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  letter-spacing: 1px;
}

.topics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.topic-select-btn {
  padding: 10px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: flex-start;
  font-family: monospace;
}

.topic-select-btn.active {
  background: var(--bg-glass-strong);
  border-color: var(--neon-primary);
  color: var(--neon-bright);
  box-shadow: var(--shadow-neon);
}

.topic-icon {
  font-size: 16px;
}

.btn-group {
  display: flex;
  gap: 8px;
}

.btn-group .btn-ghost {
  flex: 1;
  font-family: monospace;
}

.btn-group .btn-ghost.active {
  background: var(--bg-glass-strong);
  border-color: var(--neon-primary);
  color: var(--neon-bright);
  box-shadow: var(--shadow-neon);
}

.btn-group .btn-ghost.locked {
  opacity: 0.4;
  border-style: dashed;
}

.premium-hint {
  font-size: 11px;
  font-family: monospace;
  margin-top: 8px;
  color: var(--text-muted);
}

.premium-hint span {
  cursor: pointer;
  text-decoration: underline;
}

.range-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cyber-range {
  width: 100%;
  accent-color: var(--neon-primary);
}

.error-msg {
  color: var(--accent-red);
  font-family: monospace;
  margin-bottom: 16px;
}

.start-btn {
  width: 100%;
  font-family: monospace;
  letter-spacing: 3px;
  font-size: 18px;
  padding: 20px;
}

/* Searching */
.center-all {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 80vh;
}

.cyber-radar {
  width: 200px;
  height: 200px;
  border-radius: 50%;
  position: relative;
  overflow: hidden;
  margin-bottom: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(168, 85, 247, 0.05);
}

.scan-line {
  position: absolute;
  top: 0;
  left: 50%;
  width: 50%;
  height: 50%;
  background: linear-gradient(to right, transparent, var(--neon-glow));
  transform-origin: bottom left;
  animation: radarSpin 2s linear infinite;
}

@keyframes radarSpin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.data-stream {
  font-family: monospace;
  color: var(--neon-bright);
  font-size: 10px;
  opacity: 0.5;
  text-align: center;
  word-break: break-all;
  padding: 20px;
  z-index: 1;
}

.pulse-text {
  font-family: monospace;
  letter-spacing: 2px;
  animation: pulseOpacity 1.5s infinite;
}

@keyframes pulseOpacity {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.cancel-btn {
  margin-top: 40px;
  font-family: monospace;
}

/* Match */
.match-icon {
  font-size: 80px;
  margin-bottom: 20px;
  animation: neonPulse 1s infinite alternate;
}

.cyber-text {
  font-family: monospace;
  color: var(--text-secondary);
  margin-top: 10px;
}

/* Custom Checkbox */
.cyber-checkbox {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  position: relative;
}

.cyber-checkbox input {
  position: absolute;
  opacity: 0;
  cursor: pointer;
}

.checkmark {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  background: var(--bg-input);
}

.cyber-checkbox input:checked ~ .checkmark {
  background: var(--neon-primary);
  box-shadow: var(--shadow-neon);
}

.cyber-checkbox input:checked ~ .checkmark::after {
  content: '';
  width: 6px;
  height: 12px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.label-text {
  font-family: monospace;
  font-size: 13px;
}
</style>
