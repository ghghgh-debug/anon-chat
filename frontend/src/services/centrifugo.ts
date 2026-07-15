/**
 * Centrifugo real-time client.
 * 
 * Manages WebSocket connection to Centrifugo for live chat messaging,
 * match notifications, and typing indicators.
 */

import { Centrifuge, Subscription } from 'centrifuge'
import type { PublicationContext } from 'centrifuge'

let CENTRIFUGO_URL = import.meta.env.VITE_CENTRIFUGO_URL || 'ws://localhost:8000/connection/websocket'

if (typeof window !== 'undefined') {
  const origin = window.location.origin
  if (origin.includes('anon-chat-frontend')) {
    const rawCentrifugo = origin.replace('anon-chat-frontend', 'anon-chat-centrifugo')
    let wsUrl = rawCentrifugo
    if (wsUrl.startsWith('http://') || wsUrl.startsWith('https://')) {
      wsUrl = wsUrl.replace(/^http/, 'ws')
    }
    if (!wsUrl.endsWith('/connection/websocket') && !wsUrl.endsWith('/connection/websocket/')) {
      wsUrl = wsUrl.endsWith('/') ? `${wsUrl}connection/websocket` : `${wsUrl}/connection/websocket`
    }
    CENTRIFUGO_URL = wsUrl
  }
}

let centrifuge: Centrifuge | null = null
const subscriptions: Map<string, Subscription> = new Map()

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

/**
 * Connect to Centrifugo with a connection token.
 */
export function connectCentrifugo(token: string): Centrifuge {
  if (centrifuge) {
    centrifuge.disconnect()
  }

  centrifuge = new Centrifuge(CENTRIFUGO_URL, {
    token,
  })

  centrifuge.on('connected', () => {
    console.log('[Centrifugo] Connected')
  })

  centrifuge.on('disconnected', (ctx) => {
    console.log('[Centrifugo] Disconnected:', ctx.reason)
  })

  centrifuge.on('error', (ctx) => {
    console.error('[Centrifugo] Error:', ctx)
  })

  centrifuge.connect()
  return centrifuge
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
): Subscription {
  if (!centrifuge) {
    throw new Error('Centrifugo not connected')
  }

  // Unsubscribe from existing subscription on same channel
  if (subscriptions.has(channel)) {
    subscriptions.get(channel)!.unsubscribe()
    subscriptions.delete(channel)
  }

  const sub = centrifuge.newSubscription(channel, {
    token,
  })

  sub.on('publication', (ctx: PublicationContext) => {
    onMessage(ctx.data as ChatMessage)
  })

  if (onSubscribed) {
    sub.on('subscribed', onSubscribed)
  }

  if (onUnsubscribed) {
    sub.on('unsubscribed', onUnsubscribed)
  }

  sub.on('error', (ctx) => {
    console.error(`[Centrifugo] Subscription error on ${channel}:`, ctx)
  })

  sub.subscribe()
  subscriptions.set(channel, sub)

  return sub
}

/**
 * Unsubscribe from a specific channel.
 */
export function unsubscribeFromChannel(channel: string): void {
  const sub = subscriptions.get(channel)
  if (sub) {
    sub.unsubscribe()
    subscriptions.delete(channel)
  }
}

/**
 * Disconnect from Centrifugo and clean up all subscriptions.
 */
export function disconnectCentrifugo(): void {
  subscriptions.forEach((sub) => sub.unsubscribe())
  subscriptions.clear()

  if (centrifuge) {
    centrifuge.disconnect()
    centrifuge = null
  }
}

/**
 * Get the current Centrifugo instance.
 */
export function getCentrifuge(): Centrifuge | null {
  return centrifuge
}
