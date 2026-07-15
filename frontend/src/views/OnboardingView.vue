<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { userApi } from '../api'
import { appLanguage, setAppLanguage, topicOptions, type AppLanguage, t } from '../i18n'

const router = useRouter()
const step = ref(0)
const loading = ref(false)
const error = ref('')

const agreedToRules = ref(false)
const age = ref(14)
const gender = ref('')
const selectedTopics = ref<string[]>([])
const nickname = ref('')

const availableTopics = topicOptions
const languageOptions: [AppLanguage, string][] = [['ru', 'Русский'], ['en', 'English'], ['uz', "O'zbekcha"]]

const canProceed = computed(() => {
  switch (step.value) {
    case 0: return true
    case 1: return agreedToRules.value
    case 2: return age.value >= 14 && age.value <= 99
    case 3: return gender.value !== ''
    case 4: return selectedTopics.value.length > 0
    case 5: return nickname.value.trim().length >= 2
    case 6: return true
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
  if (canProceed.value && step.value < 6) step.value++
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
      app_language: appLanguage.value,
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
      <div class="progress-fill" :style="{ width: `${((step + 1) / 7) * 100}%` }"></div>
      </div>
      <div class="progress-text neon-text">SYS.INIT.{{ step + 1 }}/7</div>
    </div>

    <!-- Step 0: interface language, before any other app content -->
    <div v-if="step === 0" class="step slide-up">
      <div class="cyber-icon neon-text">🌐</div>
      <h2 class="neon-text">{{ t('chooseLanguage') }}</h2>
      <div class="gender-grid">
        <div v-for="lang in languageOptions" :key="lang[0]" class="glass-card gender-card" :class="{ active: appLanguage === lang[0] }" @click="setAppLanguage(lang[0])"><span>{{ lang[1] }}</span></div>
      </div>
    </div>

    <!-- Step 0: Rules -->
    <div v-if="step === 1" class="step slide-up">
      <div class="cyber-icon neon-text">⚠</div>
      <h2 class="neon-text">USER_AGREEMENT</h2>
      
      <div class="glass-card rules-box">
        <ul>
          <li>Access restricted to users <strong>14+</strong></li>
          <li>No spam, scams, or abuse</li>
          <li>Violations result in permanent ban</li>
        </ul>
      </div>
      
      <label class="cyber-checkbox">
        <input type="checkbox" v-model="agreedToRules" />
        <span class="checkmark neon-border"></span>
        <span class="label-text">I am 14+ and agree to the rules</span>
      </label>
    </div>

    <!-- Step 1: Age -->
    <div v-if="step === 2" class="step slide-up">
      <div class="cyber-icon neon-text">AGE</div>
      <h2 class="neon-text">INPUT_AGE</h2>
      <div class="age-selector">
        <button class="btn-ghost" @click="age = Math.max(14, age - 1)">-</button>
        <div class="age-display neon-text">{{ age }}</div>
        <button class="btn-ghost" @click="age = Math.min(99, age + 1)">+</button>
      </div>
      <input type="range" v-model.number="age" min="14" max="99" class="cyber-range" />
    </div>

    <!-- Step 2: Gender -->
    <div v-if="step === 3" class="step slide-up">
      <div class="cyber-icon neon-text">SEX</div>
      <h2 class="neon-text">SELECT_GENDER</h2>
      <div class="gender-grid">
        <div class="glass-card gender-card" :class="{ active: gender === 'male' }" @click="gender = 'male'">
          <span class="g-icon">M</span>
          <span>MALE</span>
        </div>
        <div class="glass-card gender-card" :class="{ active: gender === 'female' }" @click="gender = 'female'">
          <span class="g-icon">F</span>
          <span>FEMALE</span>
        </div>
      </div>
    </div>

    <!-- Step 3: Topics -->
    <div v-if="step === 4" class="step slide-up">
      <div class="cyber-icon neon-text">TAGS</div>
      <h2 class="neon-text">SELECT_INTERESTS</h2>
      <div class="topics-container">
        <div 
          v-for="topic in availableTopics" 
          :key="topic.id"
          class="topic-tag glass-card"
          :class="{ active: selectedTopics.includes(topic.id) }"
          @click="toggleTopic(topic.id)"
        >
          {{ topic.icon }} {{ topic[appLanguage] }}
        </div>
      </div>
    </div>

    <!-- Step 4: Nickname -->
    <div v-if="step === 5" class="step slide-up">
      <div class="cyber-icon neon-text">ID</div>
      <h2 class="neon-text">ENTER_ALIAS</h2>
      <input 
        v-model="nickname" 
        type="text" 
        class="input-neon cyber-input" 
        placeholder="> alias_"
        maxlength="50"
      />
    </div>

    <!-- Step 5: Confirm -->
    <div v-if="step === 6" class="step slide-up">
      <div class="cyber-icon neon-text">OK</div>
      <h2 class="neon-text">CONFIRM_DATA</h2>
      <div class="glass-card summary-card">
        <div class="s-row"><span>ALIAS:</span> <span class="neon-text">{{ nickname }}</span></div>
        <div class="s-row"><span>AGE:</span> <span class="neon-text">{{ age }}</span></div>
        <div class="s-row"><span>SEX:</span> <span class="neon-text">{{ gender.toUpperCase() }}</span></div>
        <div class="s-row"><span>TAGS:</span> 
          <div class="s-tags">
            <span v-for="t in selectedTopics" :key="t" class="s-tag">{{ topicOptions.find(topic => topic.id === t)?.icon }} {{ topicOptions.find(topic => topic.id === t)?.[appLanguage] }}</span>
          </div>
        </div>
      </div>
      <p v-if="error" style="color: var(--accent-red); margin-top: 16px;">ERR: {{ error }}</p>
    </div>

    <!-- Navigation -->
    <div class="nav-bar">
      <button v-if="step > 0" class="btn-ghost" @click="prevStep">&lt; BACK</button>
      <div v-else></div>
      
      <button v-if="step < 6" class="btn-neon" :disabled="!canProceed" @click="nextStep">{{ step === 0 ? t('continue') : 'NEXT >' }}</button>
      <button v-if="step === 6" class="btn-neon" :disabled="loading" @click="submit">
        {{ loading ? 'PROCESSING...' : 'EXECUTE' }}
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
