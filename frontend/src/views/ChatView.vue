<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { chatApi, userApi } from '../api'
import { connectCentrifugo, subscribeToChannel, disconnectCentrifugo, type ChatMessage } from '../services/centrifugo'

const router = useRouter()
const route = useRoute()

const chatId = parseInt(route.params.chatId as string)
const channel = route.query.channel as string
const token = route.query.token as string

const user = ref<any>(null)
const messages = ref<ChatMessage[]>([])
const inputMsg = ref('')
const isTyping = ref(false)
const partnerTyping = ref(false)
const chatActive = ref(true)
const chatEndedReason = ref('')

let typingTimeout: number | null = null
let partnerTypingTimeout: number | null = null

const messagesContainer = ref<HTMLElement | null>(null)

// For Report/Rate modals
const showRateModal = ref(false)
const showReportModal = ref(false)
const reportCategory = ref('spam')
const rating = ref('like')

onMounted(async () => {
  try {
    user.value = await userApi.getMe()
    
    // Connect to chat channel
    const centrifuge = connectCentrifugo(token)
    subscribeToChannel(channel, token, handleIncomingMessage)
    
    // If it's a real chat ID (not a room UUID), fetch history
    if (!isNaN(chatId)) {
      const history = await chatApi.getMessages(chatId)
      messages.value = history.messages || []
      scrollToBottom()
    }
  } catch (e: any) {
    console.error('Chat error:', e.message)
    router.push('/')
  }
})

onUnmounted(() => {
  disconnectCentrifugo()
})

function handleIncomingMessage(msg: ChatMessage) {
  if (msg.event === 'message') {
    messages.value.push(msg)
    if (msg.sender_id !== user.value.id) {
      partnerTyping.value = false
    }
    scrollToBottom()
  } else if (msg.event === 'typing' && msg.sender_id !== user.value.id) {
    partnerTyping.value = true
    if (partnerTypingTimeout) clearTimeout(partnerTypingTimeout)
    partnerTypingTimeout = window.setTimeout(() => {
      partnerTyping.value = false
    }, 3000)
  } else if (msg.event === 'chat_ended') {
    chatActive.value = false
    chatEndedReason.value = msg.reason || 'manual'
    showRateModal.value = true
  }
}

async function sendMessage() {
  if (!inputMsg.value.trim() || !chatActive.value) return
  const txt = inputMsg.value
  inputMsg.value = ''
  
  try {
    await chatApi.sendMessage({
      chat_id: chatId,
      type: 'text',
      content: txt,
    })
  } catch (e) {
    console.error('Send error:', e)
  }
}

function handleInput() {
  if (!isTyping.value) {
    isTyping.value = true
    chatApi.typing(channel).catch(() => {})
  }
  if (typingTimeout) clearTimeout(typingTimeout)
  typingTimeout = window.setTimeout(() => {
    isTyping.value = false
  }, 2000)
}

async function endChat() {
  if (!confirm('END_CONNECTION?')) return
  try {
    await chatApi.endChat(chatId)
    chatActive.value = false
    showRateModal.value = true
  } catch (e) {
    console.error(e)
  }
}

async function submitReport() {
  try {
    // Determine partner ID from messages (hacky, but works if we have msgs)
    const partnerMsg = messages.value.find(m => m.sender_id !== user.value.id)
    const partnerId = partnerMsg ? partnerMsg.sender_id : 0 // Fallback
    
    await chatApi.report({
      chat_id: chatId,
      reported_id: partnerId || 0, // In prod, get this from chat metadata
      category: reportCategory.value,
    })
    showReportModal.value = false
    showRateModal.value = false
    router.push('/')
  } catch (e) {
    console.error(e)
  }
}

async function submitRating() {
  try {
    const partnerMsg = messages.value.find(m => m.sender_id !== user.value.id)
    const partnerId = partnerMsg ? partnerMsg.sender_id : 0
    
    await chatApi.rate({
      chat_id: chatId,
      to_user_id: partnerId || 0,
      value: rating.value,
    })
    showRateModal.value = false
    router.push('/')
  } catch (e) {
    console.error(e)
    router.push('/') // exit anyway
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

function formatTime(iso?: string) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<template>
  <div class="chat-view">
    <!-- Header -->
    <div class="chat-header glass-card">
      <button class="btn-ghost small-btn" @click="endChat" v-if="chatActive">&lt; END</button>
      <button class="btn-ghost small-btn" @click="router.push('/')" v-else>&lt; HOME</button>
      
      <div class="chat-title">
        <span class="neon-text">ENCRYPTED_CHANNEL</span>
        <span v-if="partnerTyping" class="typing-indicator">partner_typing...</span>
      </div>

      <button class="btn-ghost small-btn danger" @click="showReportModal = true" v-if="chatActive">REPORT</button>
    </div>

    <!-- Messages -->
    <div class="messages-container" ref="messagesContainer">
      <div class="sys-msg">CONNECTION_ESTABLISHED</div>
      
      <div 
        v-for="m in messages" 
        :key="m.id"
        class="message-wrapper"
        :class="{ 'my-message': m.sender_id === user?.id }"
      >
        <div class="message-bubble" :class="{ 'neon-border': m.sender_id === user?.id }">
          <div v-if="m.type === 'text'" class="msg-content">{{ m.content }}</div>
          <img v-else-if="m.type === 'photo'" :src="m.content" class="msg-img" />
          <div class="msg-time">{{ formatTime(m.sent_at) }}</div>
        </div>
      </div>

      <div v-if="!chatActive" class="sys-msg alert">CONNECTION_TERMINATED ({{ chatEndedReason }})</div>
    </div>

    <!-- Input -->
    <div class="chat-input-area glass-card" v-if="chatActive">
      <input 
        v-model="inputMsg" 
        type="text" 
        class="input-neon cyber-input" 
        placeholder="> input_data..." 
        @input="handleInput"
        @keyup.enter="sendMessage"
      />
      <button class="btn-neon send-btn" @click="sendMessage">TX</button>
    </div>

    <!-- Rate Modal -->
    <div v-if="showRateModal" class="modal-overlay fade-in">
      <div class="glass-card modal-content neon-border">
        <h3 class="neon-text">RATE_CONNECTION</h3>
        <p class="cyber-desc">How was your interaction?</p>
        
        <div class="rate-buttons">
          <button class="btn-ghost" :class="{ active: rating === 'like' }" @click="rating = 'like'">👍 LIKE</button>
          <button class="btn-ghost" :class="{ active: rating === 'dislike' }" @click="rating = 'dislike'">👎 DISLIKE</button>
        </div>
        
        <button class="btn-neon full-w" @click="submitRating">SUBMIT</button>
        <button class="btn-ghost full-w mt-2" @click="router.push('/')">SKIP</button>
      </div>
    </div>

    <!-- Report Modal -->
    <div v-if="showReportModal" class="modal-overlay fade-in">
      <div class="glass-card modal-content" style="border-color: var(--accent-red)">
        <h3 style="color: var(--accent-red)">REPORT_USER</h3>
        <p class="cyber-desc">Select violation type:</p>
        
        <select v-model="reportCategory" class="input-neon mb-3">
          <option value="spam">SPAM</option>
          <option value="insult">INSULT</option>
          <option value="nsfw">NSFW</option>
          <option value="scam">SCAM</option>
          <option value="other">OTHER</option>
        </select>
        
        <button class="btn-neon full-w" style="background: var(--accent-red)" @click="submitReport">EXECUTE_REPORT</button>
        <button class="btn-ghost full-w mt-2" @click="showReportModal = false">CANCEL</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-deep);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-radius: 0 0 16px 16px;
  border-top: none;
  z-index: 10;
}

.small-btn {
  padding: 8px 12px;
  font-size: 12px;
}

.danger {
  color: var(--accent-red);
  border-color: rgba(244, 63, 94, 0.4);
}

.chat-title {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-family: monospace;
  font-weight: 700;
  letter-spacing: 1px;
}

.typing-indicator {
  font-size: 10px;
  color: var(--accent-cyan);
  animation: pulseOpacity 1s infinite;
}

@keyframes pulseOpacity {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sys-msg {
  text-align: center;
  font-family: monospace;
  font-size: 11px;
  color: var(--text-muted);
  margin: 16px 0;
  letter-spacing: 1px;
}

.sys-msg.alert {
  color: var(--accent-red);
}

.message-wrapper {
  display: flex;
  justify-content: flex-start;
}

.message-wrapper.my-message {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 75%;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 16px 16px 16px 4px;
  padding: 10px 14px;
  position: relative;
}

.my-message .message-bubble {
  background: var(--bg-glass-strong);
  border-radius: 16px 16px 4px 16px;
}

.msg-content {
  font-size: 15px;
  line-height: 1.4;
  word-wrap: break-word;
}

.msg-img {
  max-width: 100%;
  border-radius: 8px;
  margin-bottom: 4px;
}

.msg-time {
  font-size: 10px;
  color: var(--text-muted);
  text-align: right;
  margin-top: 4px;
  font-family: monospace;
}

.chat-input-area {
  display: flex;
  gap: 8px;
  padding: 12px;
  border-radius: 16px 16px 0 0;
  border-bottom: none;
}

.cyber-input {
  font-family: monospace;
}

.send-btn {
  padding: 0 20px;
  font-family: monospace;
  font-size: 16px;
}

/* Modals */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.8);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
}

.modal-content {
  width: 100%;
  max-width: 320px;
  padding: 24px;
  text-align: center;
}

.cyber-desc {
  font-family: monospace;
  color: var(--text-secondary);
  margin-bottom: 20px;
  font-size: 12px;
}

.rate-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.rate-buttons .btn-ghost {
  flex: 1;
}

.rate-buttons .active {
  background: var(--bg-glass-strong);
  color: var(--neon-bright);
}

.full-w {
  width: 100%;
}

.mt-2 {
  margin-top: 12px;
}

.mb-3 {
  margin-bottom: 20px;
}
</style>
