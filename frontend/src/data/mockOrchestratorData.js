// ─── Mock Data for AI Orchestrator & Workflow Pipeline ───────────────────
// This file provides static reference data and initial mock values.
// Dynamic state (configured models, channels) lives in the Zustand store.

/**
 * The fixed Auto-Orchestrator option.
 * This is always available regardless of configured models.
 */
export const AUTO_ORCHESTRATOR = {
  id: 'auto-orchestrator',
  name: '✨ Auto-Orchestrator',
  description: 'AI memilih model & workflow terbaik secara otomatis',
}

/**
 * User-created workflows (orchestration pipelines).
 * Each workflow has an `id`, `name` (display name with emoji), and optional `description`.
 * → Replace with API call: api.listWorkflows()
 */
export const MOCK_WORKFLOWS = [
  { id: 'wf-analisis-laporan', name: '⚙️ Workflow Analisis Laporan',  description: 'Analisis laporan keuangan otomatis' },
  { id: 'wf-riset-data',      name: '⚙️ Workflow Riset Data',        description: 'Riset dan rangkum data dari internet' },
  { id: 'wf-auto-reply',      name: '⚙️ Workflow Auto Reply',        description: 'Balas pesan Telegram otomatis' },
]

/**
 * INITIAL_MOCK_MODELS — sample models that the Integrasi page would push into
 * the Zustand store via `setActiveConfiguredModels(INITIAL_MOCK_MODELS)`.
 *
 * The Workflow Editor also references this for its step model dropdowns.
 *
 * In production, these come from:
 *   → api.getConfiguredModels() or the Integrasi Platform -> Model AI section
 */
export const INITIAL_MOCK_MODELS = [
  { id: 'gemini-2.5-pro',   name: '🧠 Gemini-2.5-Pro',    provider: 'Google' },
  { id: 'gemini-2.5-flash', name: '🧠 Gemini-2.5-Flash',  provider: 'Google' },
  { id: 'claude-3-haiku',   name: '🧠 Claude-3-Haiku',    provider: 'Anthropic' },
  { id: 'claude-3-sonnet',  name: '🧠 Claude-3-Sonnet',   provider: 'Anthropic' },
  { id: 'gpt-4o',           name: '🧠 GPT-4o',            provider: 'OpenAI' },
  { id: 'llama-3',          name: '🧠 Llama-3',           provider: 'Meta' },
]

/**
 * MOCK_CONNECTED_CHANNELS — sample channels for the Channel Selector.
 * In production these come from:
 *   → api.getConnectedChannels() or webhook configs
 */
export const MOCK_CONNECTED_CHANNELS = [
  { id: 'web-chat',  name: '🌐 Web Chat (Main)', type: 'web',      isDefault: true },
  { id: 'whatsapp',  name: '💬 WhatsApp',         type: 'whatsapp', isDefault: false },
  { id: 'telegram',  name: '✈️ Telegram',         type: 'telegram', isDefault: false },
]
