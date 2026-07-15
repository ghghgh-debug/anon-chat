/**
 * API client for communicating with the backend.
 * 
 * Uses Telegram WebApp initData as the authentication token
 * in the Authorization header on every request.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080/api'

function getInitData(): string {
  if (window.Telegram?.WebApp?.initData) {
    return window.Telegram.WebApp.initData
  }
  return ''
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `tma ${getInitData()}`,
    ...(options.headers as Record<string, string> || {}),
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `HTTP ${resp.status}`)
  }

  return resp.json()
}

// --- User API ---

export const userApi = {
  getMe: () => request<any>('/users/me'),

  onboarding: (data: {
    nickname: string
    age: number
    gender: string
    topics: string[]
    avatar_url?: string
    bio?: string
    agreed_to_rules: boolean
  }) => request<any>('/users/onboarding', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  updateProfile: (data: Record<string, any>) =>
    request<any>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  getLeaderboard: () => request<any>('/users/leaderboard'),

  addToBlacklist: (blockedUserId: number) =>
    request<any>('/users/blacklist', {
      method: 'POST',
      body: JSON.stringify({ blocked_user_id: blockedUserId }),
    }),
}

// --- Chat API ---

export const chatApi = {
  search: (filters: {
    find_gender?: string
    age_from?: number
    age_to?: number
    topics?: string[]
    vip_only?: boolean
  }) => request<any>('/chat/search', {
    method: 'POST',
    body: JSON.stringify(filters),
  }),

  cancelSearch: () => request<any>('/chat/cancel-search', { method: 'POST' }),

  sendMessage: (data: {
    chat_id: number
    type: string
    content: string
  }) => request<any>('/chat/send', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  typing: (channel: string) =>
    request<any>('/chat/typing', {
      method: 'POST',
      body: JSON.stringify({ channel }),
    }),

  endChat: (chatId: number) =>
    request<any>(`/chat/end?chat_id=${chatId}`, { method: 'POST' }),

  rate: (data: { chat_id: number; to_user_id: number; value: string }) =>
    request<any>('/chat/rate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  report: (data: {
    chat_id: number
    reported_id: number
    category: string
  }) => request<any>('/chat/report', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getArchive: () => request<any>('/chat/archive'),

  getMessages: (chatId: number, limit = 50, offset = 0) =>
    request<any>(`/chat/messages/${chatId}?limit=${limit}&offset=${offset}`),

  getOnlineCount: () => request<any>('/chat/online-count'),

  heartbeat: () => request<any>('/chat/heartbeat', { method: 'POST' }),

  uploadMedia: async (chatId: number, file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const resp = await fetch(`${API_BASE}/chat/upload-media?chat_id=${chatId}`, {
      method: 'POST',
      headers: {
        Authorization: `tma ${getInitData()}`,
      },
      body: formData,
    })

    if (!resp.ok) {
      const error = await resp.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(error.detail)
    }
    return resp.json()
  },
}

// --- Payment API ---

export const paymentApi = {
  createInvoice: (type: string) =>
    request<any>('/payments/create-invoice', {
      method: 'POST',
      body: JSON.stringify({ type }),
    }),

  getHistory: () => request<any>('/payments/history'),

  getPrices: () => request<any>('/payments/prices'),
}

// --- Admin API ---

export const adminApi = {
  getStats: () => request<any>('/admin/stats'),

  getReports: (limit = 50, offset = 0) =>
    request<any>(`/admin/reports?limit=${limit}&offset=${offset}`),

  resolveReport: (reportId: number, action: string) =>
    request<any>(`/admin/reports/${reportId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  banUser: (userId: number) =>
    request<any>(`/admin/users/${userId}/ban`, { method: 'POST' }),

  unbanUser: (userId: number) =>
    request<any>(`/admin/users/${userId}/unban`, { method: 'POST' }),

  createReferral: (code?: string) =>
    request<any>('/admin/referrals', {
      method: 'POST',
      body: JSON.stringify({ code: code || null }),
    }),

  getReferrals: () => request<any>('/admin/referrals'),

  getLogs: (limit = 100) => request<any>(`/admin/logs?limit=${limit}`),
}
