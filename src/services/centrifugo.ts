import { Centrifuge } from 'centrifuge'

const VITE_CENTRIFUGO_URL = import.meta.env.VITE_CENTRIFUGO_URL

/**
 * Mock Centrifugo real-time client.
 * 
 * Multiplexes over standard WebSockets connected directly to our Express server.
 * Simulates the Centrifuge API exactly to insulate the rest of the application.
 */

export interface ChatMessage {
  event: string
  id?: number
  chat_id?: number
  sender_id?: number
  type?: string
  content?: string
  sent_at?: string
  reason?: string
  ended_by?: number
  // Match event fields
  room_key?: string
  channel?: string
  token?: string
  partner?: {
    nickname: string
    age: number
    gender: string
    is_premium: boolean
  }
}

class MockSubscription {
  channel: string
  callbacks: Record<string, Function[]> = {}

  constructor(channel: string) {
    this.channel = channel
  }

  on(event: string, cb: Function) {
    if (!this.callbacks[event]) this.callbacks[event] = []
    this.callbacks[event].push(cb)
  }

  subscribe() {
    if (globalSocket && globalSocket.readyState === WebSocket.OPEN) {
      globalSocket.send(JSON.stringify({ type: 'subscribe', channel: this.channel }))
    }
  }

  unsubscribe() {
    if (globalSocket && globalSocket.readyState === WebSocket.OPEN) {
      globalSocket.send(JSON.stringify({ type: 'unsubscribe', channel: this.channel }))
    }
  }
}

let globalSocket: WebSocket | null = null
const subMap: Map<string, any> = new Map()
let centrifugeInstance: any = null

class MockCentrifuge {
  url: string
  callbacks: Record<string, Function[]> = {}

  constructor(url: string, options?: any) {
    this.url = url
  }

  on(event: string, cb: Function) {
    if (!this.callbacks[event]) this.callbacks[event] = []
    this.callbacks[event].push(cb)
  }

  connect() {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProto}//${window.location.host}/ws`
    
    console.log('[MockCentrifugo] Connecting to WebSocket:', wsUrl)
    globalSocket = new WebSocket(wsUrl)
    
    globalSocket.onopen = () => {
      console.log('[MockCentrifugo] Connected successfully')
      this.trigger('connected', {})
      // Auto-resubscribe any subscriptions added before connection was open
      for (const [_, sub] of subMap.entries()) {
        sub.subscribe()
      }
    }
    
    globalSocket.onclose = (e) => {
      console.log('[MockCentrifugo] Connection closed:', e.reason)
      this.trigger('disconnected', { reason: e.reason })
    }
    
    globalSocket.onerror = (err) => {
      console.error('[MockCentrifugo] Socket error:', err)
      this.trigger('error', err)
    }
    
    globalSocket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.type === 'publication' && payload.channel) {
          const sub = subMap.get(payload.channel)
          if (sub && sub.callbacks['publication']) {
            sub.callbacks['publication'].forEach(cb => cb({ data: payload.data }))
          }
        }
      } catch (err) {
        console.error('[MockCentrifugo] Parse error:', err)
      }
    }
  }

  disconnect() {
    if (globalSocket) {
      globalSocket.close()
      globalSocket = null
    }
    this.trigger('disconnected', { reason: 'manual' })
  }

  newSubscription(channel: string, options?: any) {
    let sub = subMap.get(channel)
    if (!sub) {
      sub = new MockSubscription(channel)
      subMap.set(channel, sub)
    }
    return sub
  }

  trigger(event: string, data: any) {
    if (this.callbacks[event]) {
      this.callbacks[event].forEach(cb => cb(data))
    }
  }
}

/**
 * Connect to Centrifugo with a connection token.
 */
export function connectCentrifugo(token: string): any {
  if (centrifugeInstance) {
    centrifugeInstance.disconnect()
  }

  if (VITE_CENTRIFUGO_URL) {
    let wsUrl = VITE_CENTRIFUGO_URL
    if (wsUrl.startsWith('http://') || wsUrl.startsWith('https://')) {
      wsUrl = wsUrl.replace(/^http/, 'ws')
      if (!wsUrl.endsWith('/connection/websocket') && !wsUrl.endsWith('/connection/websocket/')) {
        wsUrl = wsUrl.endsWith('/') ? `${wsUrl}connection/websocket` : `${wsUrl}/connection/websocket`
      }
    }
    console.log('[Centrifugo] Connecting to production Centrifugo:', wsUrl)
    centrifugeInstance = new Centrifuge(wsUrl, {
      token: token
    })
    centrifugeInstance.connect()
  } else {
    console.log('[Centrifugo] VITE_CENTRIFUGO_URL not set, using mock client')
    centrifugeInstance = new MockCentrifuge('/ws')
    centrifugeInstance.connect()
  }
  return centrifugeInstance
}

/**
 * Subscribe to a channel with a subscription token.
 * Returns the subscription object.
 */
export function subscribeToChannel(
  channel: string,
  token: string,
  onMessage: (msg: ChatMessage) => void,
  onSubscribed?: () => void,
  onUnsubscribed?: () => void,
): any {
  if (!centrifugeInstance) {
    throw new Error('Centrifugo not connected')
  }

  if (subMap.has(channel)) {
    subMap.get(channel)!.unsubscribe()
    subMap.delete(channel)
  }

  const sub = VITE_CENTRIFUGO_URL 
    ? centrifugeInstance.newSubscription(channel, { token: token })
    : centrifugeInstance.newSubscription(channel)
  
  sub.on('publication', (ctx: any) => {
    onMessage(ctx.data)
  })

  sub.subscribe()
  subMap.set(channel, sub)

  if (onSubscribed) {
    setTimeout(onSubscribed, 100) // Sim simulated confirmation
  }

  return sub
}

/**
 * Unsubscribe from a specific channel.
 */
export function unsubscribeFromChannel(channel: string): void {
  const sub = subMap.get(channel)
  if (sub) {
    sub.unsubscribe()
    subMap.delete(channel)
  }
}

/**
 * Disconnect from Centrifugo and clean up all subscriptions.
 */
export function disconnectCentrifugo(): void {
  subMap.forEach((sub) => sub.unsubscribe())
  subMap.clear()

  if (centrifugeInstance) {
    centrifugeInstance.disconnect()
    centrifugeInstance = null
  }
}

/**
 * Get the current Centrifugo instance.
 */
export function getCentrifuge(): any {
  return centrifugeInstance
}
