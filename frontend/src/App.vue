<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <RouterView v-slot="{ Component }">
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
