<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { currentLang, type Language, translations } from './services/i18n'

const hasSelectedLang = ref(true)

onMounted(() => {
  const saved = localStorage.getItem('app_lang')
  if (!saved) {
    hasSelectedLang.value = false
  }
})

function selectLanguage(lang: Language) {
  currentLang.value = lang
  localStorage.setItem('app_lang', lang)
  hasSelectedLang.value = true
}
</script>

<template>
  <div class="app-shell">
    <!-- Language Selector Overlay at Startup -->
    <div v-if="!hasSelectedLang" class="lang-overlay fade-in">
      <div class="glass-card lang-card neon-border">
        <h2 class="neon-text">SELECT LANGUAGE</h2>
        <h3 class="neon-text">ВЫБЕРИТЕ ЯЗЫК</h3>
        <h3 class="neon-text">TILNI TANLANG</h3>
        <p class="cyber-desc">Choose your interface language / Выберите язык интерфейса / Interfeys tilini tanlang</p>
        
        <div class="lang-buttons">
          <button class="btn-neon" @click="selectLanguage('ru')">РУССКИЙ</button>
          <button class="btn-neon" @click="selectLanguage('en')">ENGLISH</button>
          <button class="btn-neon" @click="selectLanguage('uz')">O'ZBEKCHA</button>
        </div>
      </div>
    </div>

    <RouterView v-else v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </RouterView>
  </div>
</template>

<style>
.app-shell {
  min-height: 100vh;
  position: relative;
}

/* Lang overlay */
.lang-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-deep);
  background-image:
    linear-gradient(rgba(168, 85, 247, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(168, 85, 247, 0.04) 1px, transparent 1px);
  background-size: 40px 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 24px;
}

.lang-card {
  width: 100%;
  max-width: 400px;
  padding: 40px 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.lang-card h2 {
  font-size: 24px;
  font-weight: 900;
  letter-spacing: 2px;
}

.lang-card h3 {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1.5px;
}

.cyber-desc {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 16px;
}

.lang-buttons {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.lang-buttons .btn-neon {
  width: 100%;
  padding: 16px;
  font-size: 16px;
  letter-spacing: 1px;
}

/* Page transition */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateX(12px);
}

.page-leave-to {
  opacity: 0;
  transform: translateX(-12px);
}
</style>
