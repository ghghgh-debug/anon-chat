<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { paymentApi, userApi } from '../api'

const router = useRouter()
const user = ref<any>(null)
const prices = ref<any[]>([])
const loading = ref(true)
const buying = ref(false)

onMounted(async () => {
  try {
    user.value = await userApi.getMe()
    const res = await paymentApi.getPrices()
    prices.value = res.prices
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function buyPremium(type: string) {
  buying.value = true
  try {
    const res = await paymentApi.createInvoice(type)

    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.openInvoice(res.invoice_url, (status: string) => {
        if (status === 'paid') {
          // It will be processed by webhook, just reload user after a bit
          setTimeout(async () => {
            user.value = await userApi.getMe()
            buying.value = false
          }, 2000)
        } else {
          buying.value = false
        }
      })
    } else {
      alert(`In production, this opens Telegram Invoice: ${res.invoice_url}`)
      buying.value = false
    }
  } catch (e) {
    console.error(e)
    buying.value = false
  }
}
</script>

<template>
  <div class="container fade-in">
    <div class="header">
      <button class="btn-ghost" @click="router.push('/')">&lt; BACK</button>
      <h2 class="neon-text">VIP_ACCESS</h2>
    </div>

    <div v-if="loading" class="center"><div class="cyber-spinner"></div></div>

    <div v-else class="content">
      <div v-if="user.is_premium" class="glass-card active-card slide-up">
        <h3 class="neon-text">VIP_STATUS_ACTIVE</h3>
        <p class="cyber-desc">Your premium license is valid until:</p>
        <div class="valid-until">{{ new Date(user.premium_until).toLocaleDateString() }}</div>
      </div>

      <div class="features slide-up">
        <h3 class="neon-text mb-3">VIP_FEATURES</h3>
        <ul class="feature-list">
          <li><span class="chk neon-text">✓</span> GENDER_FILTER_UNLOCKED</li>
          <li><span class="chk neon-text">✓</span> VIP_ONLY_ROOMS</li>
          <li><span class="chk neon-text">✓</span> EXCLUSIVE_BADGE</li>
          <li><span class="chk neon-text">✓</span> PRIORITY_QUEUE</li>
        </ul>
      </div>

      <div class="pricing-grid slide-up" style="animation-delay: 0.1s;">
        <div v-for="p in prices" :key="p.type" class="glass-card price-card">
          <div class="p-title">{{ p.label }}</div>
          <div class="p-price neon-text">⭐️ {{ p.stars }}</div>
          <button
            class="btn-neon full-w"
            @click="buyPremium(p.type)"
            :disabled="buying"
          >
            PURCHASE
          </button>
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

.active-card {
  padding: 24px;
  text-align: center;
  border-color: var(--accent-gold);
  background: rgba(251, 191, 36, 0.05);
  margin-bottom: 32px;
}

.cyber-desc {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-secondary);
  margin: 12px 0;
}

.valid-until {
  font-size: 24px;
  font-weight: 900;
  font-family: monospace;
  color: var(--accent-gold);
  text-shadow: 0 0 10px rgba(251, 191, 36, 0.4);
}

.features {
  margin-bottom: 32px;
}

.mb-3 { margin-bottom: 16px; }

.feature-list {
  list-style: none;
  padding: 0;
}

.feature-list li {
  font-family: monospace;
  font-size: 14px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  letter-spacing: 1px;
}

.chk {
  font-weight: 900;
  font-size: 16px;
}

.pricing-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.price-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
}

.p-title {
  font-family: monospace;
  font-size: 14px;
  color: var(--text-secondary);
}

.p-price {
  font-size: 24px;
  font-weight: 900;
  font-family: monospace;
}

.full-w { width: 100%; font-family: monospace; }
</style>
