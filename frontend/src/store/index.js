import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: 'ai-super-assistant-auth' }
  )
)

export const useUIStore = create((set) => ({
  sidebarOpen: true,
  currentPage: 'dashboard',
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setPage: (page) => set({ currentPage: page }),
}))

export const useChatStore = create((set, get) => ({
  sessions: [],
  currentSession: null,
  messages: [],
  streaming: false,
  streamingText: '',
  selectedModel: null,

  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (s) => set({ currentSession: s, messages: [] }),
  setMessages: (messages) => set({ messages }),
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setStreaming: (v) => set({ streaming: v }),
  setStreamingText: (t) => set({ streamingText: t }),
  appendStreamingText: (chunk) => set((s) => ({ streamingText: s.streamingText + chunk })),
  setSelectedModel: (m) => set({ selectedModel: m }),
  clearStreaming: () => set({ streaming: false, streamingText: '' }),
}))

export const useModelsStore = create((set) => ({
  models: [],
  setModels: (models) => set({ models }),
}))

export const useThemeStore = create(
  persist(
    (set, get) => ({
      theme: 'dark',
      toggleTheme: () => {
        const next = get().theme === 'dark' ? 'light' : 'dark'
        set({ theme: next })
        document.documentElement.setAttribute('data-theme', next)
      },
      initTheme: () => {
        const t = get().theme || 'dark'
        document.documentElement.setAttribute('data-theme', t)
      },
    }),
    { name: 'ai-super-assistant-theme' }
  )
)
