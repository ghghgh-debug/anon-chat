<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { userApi } from '../api'
import { t, currentLang } from '../services/i18n'

const router = useRouter()
const step = ref(0)
const loading = ref(false)
const error = ref('')

const agreedToRules = ref(false)
const age = ref(14)
const gender = ref('')
const selectedTopics = ref<string[]>([])
const nickname = ref('')
const referralCode = ref('')

const availableTopics = computed(() => [
  t('topic_chat'), t('topic_flirt'), t('topic_photos'), t('topic_games'), t('topic_life'), t('topic_nsfw'),
  '🎵 ' + (currentLang.value === 'ru' ? 'Музыка' : currentLang.value === 'uz' ? 'Musiqa' : 'Music'),
  '🎬 ' + (currentLang.value === 'ru' ? 'Кино' : currentLang.value === 'uz' ? 'Kino' : 'Cinema'),
  '💻 ' + (currentLang.value === 'ru' ? 'Технологии' : currentLang.value === 'uz' ? 'Texnologiyalar' : 'Tech'),
  '🏋️ ' + (currentLang.value === 'ru' ? 'Спорт' : currentLang.value === 'uz' ? 'Sport' : 'Sports'),
  '🎨 ' + (currentLang.value === 'ru' ? 'Искусство' : currentLang.value === 'uz' ? 'San’at' : 'Art'),
  '✈️ ' + (currentLang.value === 'ru' ? 'Путешествия' : currentLang.value === 'uz' ? 'Sayohatlar' : 'Travel'),
  '🍳 ' + (currentLang.value === 'ru' ? 'Кулинария' : currentLang.value === 'uz' ? 'Pazandachilik' : 'Cooking'),
  '🐱 ' + (currentLang.value === 'ru' ? 'Животные' : currentLang.value === 'uz' ? 'Hayvonlar' : 'Animals')
])

const canProceed = computed(() => {
  switch (step.value) {
    case 0: return agreedToRules.value
    case 1: return age.value >= 14 && age.value <= 99
    case 2: return gender.value !== ''
    case 3: return selectedTopics.value.length > 0
    case 4: return nickname.value.trim().length >= 2
    case 5: return true
    default: return false
  }
})

function toggleTopic(topic: string) {
  const idx = selectedTopics.value.indexOf(topic)
  if (idx === -1) {
    selectedTopics.value.push(topic)
  } else {
    selectedTopics.value.splice(idx, 1)
  }
}

function nextStep() {
  if (canProceed.value && step.value < 5) step.value++
}

function prevStep() {
  if (step.value > 0) step.value--
}

async function submit() {
  loading.value = true
  error.value = ''
  try {
    await userApi.onboarding({
      nickname: nickname.value.trim(),
      age: age.value,
      gender: gender.value,
      topics: selectedTopics.value,
      agreed_to_rules: true,
      referral_code: referralCode.value.trim() || undefined
    })
    router.push('/')
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container fade-in">
    <!-- Cyber Progress Bar -->
    <div class="progress-container">
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${((step + 1) / 6) * 100}%` }"></div>
      </div>
      <div class="progress-text neon-text">SYS.INIT.{{ step + 1 }}/6</div>
    </div>

    <!-- Step 0: Rules -->
    <div v-if="step === 0" class="step slide-up">
      <div class="cyber-icon neon-text">⚠</div>
      <h2 class="neon-text">{{ t('user_agreement') }}</h2>
      
      <div class="glass-card rules-box">
        <ul>
          <li>{{ t('rules_box_1') }}</li>
          <li>{{ t('rules_box_2') }}</li>
          <li>{{ t('rules_box_3') }}</li>
        </ul>
      </div>
      
      <label class="cyber-checkbox">
        <input type="checkbox" v-model="agreedToRules" />
        <span class="checkmark neon-border"></span>
        <span class="label-text">{{ t('agree_checkbox') }}</span>
      </label>
    </div>

    <!-- Step 1: Age -->
    <div v-if="step === 1" class="step slide-up">
      <div class="cyber-icon neon-text">AGE</div>
      <h2 class="neon-text">{{ t('input_age') }}</h2>
      <div class="age-selector">
        <button class="btn-ghost" @click="age = Math.max(14, age - 1)">-</button>
        <div class="age-display neon-text">{{ age }}</div>
        <button class="btn-ghost" @click="age = Math.min(99, age + 1)">+</button>
      </div>
      <input type="range" v-model.number="age" min="14" max="99" class="cyber-range" />
    </div>

    <!-- Step 2: Gender -->
    <div v-if="step === 2" class="step slide-up">
      <div class="cyber-icon neon-text">SEX</div>
      <h2 class="neon-text">{{ t('select_gender') }}</h2>
      <div class="gender-grid">
        <div class="glass-card gender-card" :class="{ active: gender === 'male' }" @click="gender = 'male'">
          <span class="g-icon">M</span>
          <span>{{ t('male') }}</span>
        </div>
        <div class="glass-card gender-card" :class="{ active: gender === 'female' }" @click="gender = 'female'">
          <span class="g-icon">F</span>
          <span>{{ t('female') }}</span>
        </div>
      </div>
    </div>

    <!-- Step 3: Topics -->
    <div v-if="step === 3" class="step slide-up">
      <div class="cyber-icon neon-text">TAGS</div>
      <h2 class="neon-text">{{ t('select_interests') }}</h2>
      <div class="topics-container">
        <div 
          v-for="topic in availableTopics" 
          :key="topic"
          class="topic-tag glass-card"
          :class="{ active: selectedTopics.includes(topic) }"
          @click="toggleTopic(topic)"
        >
          {{ topic }}
        </div>
      </div>
    </div>

    <!-- Step 4: Nickname -->
    <div v-if="step === 4" class="step slide-up">
      <div class="cyber-icon neon-text">ID</div>
      <h2 class="neon-text">{{ t('enter_alias') }}</h2>
      <input 
        v-model="nickname" 
        type="text" 
        class="input-neon cyber-input" 
        placeholder="> alias_"
        maxlength="50"
      />
    </div>

    <!-- Step 5: Confirm -->
    <div v-if="step === 5" class="step slide-up">
      <div class="cyber-icon neon-text">OK</div>
      <h2 class="neon-text">{{ t('confirm_data') }}</h2>
      <div class="glass-card summary-card">
        <div class="s-row"><span>{{ t('alias_lbl') }}</span> <span class="neon-text">{{ nickname }}</span></div>
        <div class="s-row"><span>{{ t('age_lbl') }}</span> <span class="neon-text">{{ age }}</span></div>
        <div class="s-row"><span>{{ t('sex_lbl') }}</span> <span class="neon-text">{{ gender === 'male' ? t('male') : t('female') }}</span></div>
        <div class="s-row"><span>{{ t('tags_lbl') }}</span> 
          <div class="s-tags">
            <span v-for="t in selectedTopics" :key="t" class="s-tag">{{ t }}</span>
          </div>
        </div>
        <!-- Referral Code Input field -->
        <div class="s-row mt-4">
          <span>{{ t('referral_code_lbl') }}</span>
          <input 
            v-model="referralCode" 
            type="text" 
            class="input-neon cyber-input text-left" 
            placeholder="> REF_CODE" 
            style="max-width: 100%; text-align: left; margin-top: 8px; font-size: 14px;"
          />
        </div>
      </div>
      <p v-if="error" style="color: var(--accent-red); margin-top: 16px;">ERR: {{ error }}</p>
    </div>

    <!-- Navigation -->
    <div class="nav-bar">
      <button v-if="step > 0" class="btn-ghost" @click="prevStep">{{ t('back') }}</button>
      <div v-else></div>
      
      <button v-if="step < 5" class="btn-neon" :disabled="!canProceed" @click="nextStep">{{ t('next') }}</button>
      <button v-if="step === 5" class="btn-neon" :disabled="loading" @click="submit">
        {{ loading ? t('processing') : t('execute') }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.container {
  padding: 24px;
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.progress-container {
  margin-bottom: 40px;
}

.progress-bar {
  height: 6px;
  background: rgba(255,255,255,0.05);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: var(--gradient-neon);
  box-shadow: var(--shadow-neon);
  transition: width 0.3s ease;
}

.progress-text {
  font-family: monospace;
  font-size: 12px;
  letter-spacing: 2px;
  text-align: right;
}

.step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.cyber-icon {
  font-size: 32px;
  font-weight: 900;
  font-family: monospace;
  margin-bottom: 16px;
  letter-spacing: 2px;
}

h2 {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 2px;
  margin-bottom: 32px;
}

/* Rules */
.rules-box {
  padding: 24px;
  text-align: left;
  width: 100%;
  margin-bottom: 32px;
}

.rules-box ul {
  padding-left: 20px;
}

.rules-box li {
  margin-bottom: 12px;
  font-family: monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

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

/* Age */
.age-selector {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 32px;
}

.age-selector .btn-ghost {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  padding: 0;
  font-size: 24px;
}

.age-display {
  font-size: 64px;
  font-weight: 900;
  font-family: monospace;
  width: 100px;
}

.cyber-range {
  width: 100%;
  max-width: 300px;
  accent-color: var(--neon-primary);
}

/* Gender */
.gender-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  width: 100%;
}

.gender-card {
  padding: 32px 16px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-family: monospace;
  font-weight: 700;
  letter-spacing: 1px;
}

.gender-card.active {
  border-color: var(--neon-primary);
  background: var(--bg-glass-strong);
  box-shadow: var(--shadow-neon);
  color: var(--neon-bright);
}

.g-icon {
  font-size: 32px;
}

/* Topics */
.topics-container {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}

.topic-tag {
  padding: 10px 16px;
  font-size: 13px;
  cursor: pointer;
  border-radius: var(--radius-full);
}

.topic-tag.active {
  border-color: var(--neon-primary);
  background: var(--bg-glass-strong);
  box-shadow: var(--shadow-neon);
  color: var(--neon-bright);
}

/* Nickname */
.cyber-input {
  font-family: monospace;
  font-size: 20px;
  text-align: center;
  max-width: 300px;
  letter-spacing: 2px;
}

/* Summary */
.summary-card {
  width: 100%;
  padding: 24px;
  font-family: monospace;
  font-size: 14px;
  text-align: left;
}

.s-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 16px;
}

.s-row:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.s-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.s-tag {
  background: var(--bg-glass);
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
}

/* Nav */
.nav-bar {
  display: flex;
  justify-content: space-between;
  margin-top: 40px;
}
</style>
