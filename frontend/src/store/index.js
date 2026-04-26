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
    { name: 'ai-orchestrator-auth' }
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

  // Live progress states
  processSteps: [],
  statusText: '',
  actualModel: null,
  abortRequest: null,
  
  setProcessSteps: (steps) => set({ processSteps: steps }),
  addProcessStep: (step) => set((s) => ({ processSteps: [...s.processSteps, step] })),
  setStatusText: (t) => set({ statusText: t }),
  setActualModel: (m) => set({ actualModel: m }),
  setAbortRequest: (fn) => set({ abortRequest: fn }),
}))

export const useModelsStore = create((set) => ({
  models: [],
  setModels: (models) => set({ models }),
}))

// ─── Orchestrator Store ─────────────────────────────────────────────────
// Global state for the AI Orchestrator system.
// `appName` — customizable application display name.
// `activeConfiguredModels` — populated from Integrasi Platform -> Model AI page.
// `savedWorkflows` — workflows created by the user in the Workflow Editor.
// `connectedChannels` — platforms/sessions the user has connected.
export const useOrchestratorStore = create(
  persist(
    (set) => ({
      // → Application name (editable from Profile/Settings)
      appName: 'AI ORCHESTRATOR',
      setAppName: (name) => set({ appName: name }),

      // → Models configured via Integrasi page (start empty = "belum ada model")
      //   To simulate having models, call setActiveConfiguredModels([...]) from Integrasi page
      activeConfiguredModels: [],
      setActiveConfiguredModels: (models) => set({ activeConfiguredModels: models }),

      // → Saved Workflows created by the user
      savedWorkflows: [
        { id: 'wf-analisis-laporan', name: '⚙️ Workflow Analisis Laporan', description: 'Analisis laporan keuangan otomatis', model: 'sumopod/seed-2-0-pro (Sumopod)' },
        { id: 'wf-riset-data',      name: '⚙️ Workflow Riset Data',       description: 'Riset dan rangkum data dari internet', model: 'Kombinasi (GPT-4o + Gemini 1.5)' },
        { id: 'wf-auto-reply',      name: '⚙️ Workflow Auto Reply',       description: 'Balas pesan Telegram otomatis', model: 'Llama-3-70b (Local)' },
      ],
      setSavedWorkflows: (workflows) => set({ savedWorkflows: workflows }),
      addWorkflow: (workflow) => set((s) => ({ savedWorkflows: [...s.savedWorkflows, workflow] })),
      removeWorkflow: (id) => set((s) => ({
        savedWorkflows: s.savedWorkflows.filter((w) => w.id !== id),
      })),

      // → Connected channels / sessions
      connectedChannels: [
        { id: 'web-chat',  name: '🌐 Web Chat (Main)', type: 'web',      isDefault: true },
        { id: 'whatsapp',  name: '💬 WhatsApp',         type: 'whatsapp', isDefault: false },
        { id: 'telegram',  name: '✈️ Telegram',         type: 'telegram', isDefault: false },
      ],
      setConnectedChannels: (channels) => set({ connectedChannels: channels }),

      // → Currently selected channel
      selectedChannel: 'web-chat',
      setSelectedChannel: (id) => set({ selectedChannel: id }),

      // → Currently selected orchestrator option (auto / workflow / single model)
      selectedOrchestrator: 'auto-orchestrator',
      setSelectedOrchestrator: (id) => set({ selectedOrchestrator: id }),

      // → Real-time routing info (updated live as messages stream in)
      activeModel: null,           // Model yang sedang digunakan saat ini
      activeCapability: null,      // Capability tag yang digunakan
      setActiveModel: (m) => set({ activeModel: m }),
      setActiveCapability: (c) => set({ activeCapability: c }),
      clearActiveRouting: () => set({ activeModel: null, activeCapability: null }),

      // → Capability Map cache dari backend
      capabilityMap: {},
      setCapabilityMap: (map) => set({ capabilityMap: map }),

      // → Drive Upload Prompt: konten AI yang siap di-upload ke Drive
      // Muncul setelah AI selesai menjawab dalam mode orchestrator kompleks
      drivePromptContent: null,
      drivePromptTitle: null,
      setDrivePromptContent: (content, title) => set({ drivePromptContent: content, drivePromptTitle: title }),
      clearDrivePrompt: () => set({ drivePromptContent: null, drivePromptTitle: null }),
    }),
    { 
      name: 'ai-orchestrator-orchestrator',
      partialize: (state) => ({
        appName: state.appName,
        savedWorkflows: state.savedWorkflows,
        connectedChannels: state.connectedChannels,
        selectedChannel: state.selectedChannel,
        selectedOrchestrator: state.selectedOrchestrator,
        // intentionally exclude activeConfiguredModels from persistence so it relies on live backend data
      }),
    }
  )
)

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
    { name: 'ai-orchestrator-theme' }
  )
)
