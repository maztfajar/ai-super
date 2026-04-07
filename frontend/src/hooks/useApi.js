const BASE = '/api'

function getToken() {
  try {
    const s = JSON.parse(localStorage.getItem('ai-super-assistant-auth') || '{}')
    return s?.state?.token
  } catch { return null }
}

async function req(method, path, body, opts = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = 'Bearer ' + token

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    ...opts,
  })

  if (res.status === 401) {
    localStorage.removeItem('ai-super-assistant-auth')
    window.location.href = '/login'
    return
  }

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }))
    const err = new Error(
      typeof errBody.detail === 'string'
        ? errBody.detail
        : errBody.detail?.message || errBody.message || 'Request failed'
    )
    err.detail   = errBody.detail
    err.status   = res.status
    err.response = { data: errBody }
    throw err
  }

  return res.json()
}

// Fetch tanpa redirect (untuk endpoint public sebelum login)
async function reqPublic(method, path) {
  try {
    const res = await fetch(BASE + path, { method, headers: { 'Content-Type': 'application/json' } })
    if (!res.ok) return null
    return res.json()
  } catch { return null }
}

export const api = {
  get:    (path)       => req('GET', path),
  post:   (path, body) => req('POST', path, body),
  put:    (path, body) => req('PUT', path, body),
  delete: (path)       => req('DELETE', path),

  // ── Auth ─────────────────────────────────────────────────
  login:    (username, password) => req('POST', '/auth/login', { username, password }),
  register: (username, email, password) => req('POST', '/auth/register', { username, email, password }),
  me:       () => req('GET', '/auth/me'),

  // ── User Management (Admin) ───────────────────────────────
  listUsers:  ()       => req('GET',    '/auth/users'),
  createUser: (d)      => req('POST',   '/auth/users', d),
  updateUser: (id, d)  => req('PUT',    '/auth/users/' + id, d),
  deleteUser: (id)     => req('DELETE', '/auth/users/' + id),

  // ── App Profile ───────────────────────────────────────────
  getAppProfile:   () => reqPublic('GET', '/auth/app-profile'),
  updateProfile:   (d) => req('POST', '/auth/update-profile', d),
  updateAppProfile: async function(appName, logoFile) {
    const token = getToken()
    const form  = new FormData()
    if (appName && appName.trim()) form.append('app_name', appName.trim())
    if (logoFile instanceof File)  form.append('logo', logoFile)

    // Jika tidak ada yang diubah, return early
    if (!form.has('app_name') && !form.has('logo')) {
      return { status: 'no_change' }
    }

    const res = await fetch('/api/auth/app-profile', {
      method:  'POST',
      headers: token ? { 'Authorization': 'Bearer ' + token } : {},
      body:    form,
    })
    if (!res.ok) {
      const e = await res.json().catch(function() { return {} })
      throw new Error(e.detail || 'Gagal update profil aplikasi')
    }
    return res.json()
  },

  // ── Chat ─────────────────────────────────────────────────
  createSession: (title) => req('POST', '/chat/sessions', { title }),
  listSessions:  ()      => req('GET',  '/chat/sessions?t=' + Date.now()),
  getMessages:   (id)    => req('GET',  '/chat/sessions/' + id + '/messages'),
  getNewMessages:(id, afterTs) => req('GET', '/chat/sessions/' + id + '/messages/new' + (afterTs ? '?after_ts=' + encodeURIComponent(afterTs) : '')),
  deleteSession: (id)    => req('DELETE', '/chat/sessions/' + id),
  exportChat:    async (id, format) => {
    const token = localStorage.getItem('token')
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {}
    const res = await fetch(`${API_URL}/chat/sessions/${id}/export?format=${format}`, { headers })
    if (!res.ok) throw new Error('Gagal download export chat')
    return res.blob()
  },

  // ── RAG ───────────────────────────────────────────────────
  listDocs:   ()     => req('GET',    '/rag/documents'),
  deleteDoc:  (id)   => req('DELETE', '/rag/documents/' + id),
  queryRAG:   (q)    => req('POST',   '/rag/query', { query: q }),
  scrapeWeb:  (url)  => req('POST',   '/rag/scrape', { url }),

  // ── Models ────────────────────────────────────────────────
  listModels: () => req('GET', '/models/'),

  // ── Custom Model Providers ────────────────────────────────
  listCustomModels:     ()     => req('GET',    '/integrations/custom-models'),
  addCustomModel:       (d)    => req('POST',   '/integrations/custom-models', d),
  updateCustomModel:    (id,d) => req('PUT',    '/integrations/custom-models/' + id, d),
  deleteCustomModel:    (id)   => req('DELETE', '/integrations/custom-models/' + id),
  testCustomModel:      (id)   => req('POST',   '/integrations/custom-models/' + id + '/test'),
  testCustomConnection: (d)    => req('POST',   '/integrations/custom-models/test-connection', d),

  // ── Memory ───────────────────────────────────────────────
  listMemories:  ()        => req('GET',    '/memory/'),
  addMemory:     (content) => req('POST',   '/memory/', { content }),
  deleteMemory:  (id)      => req('DELETE', '/memory/' + id),

  // ── Workflow ─────────────────────────────────────────────
  listWorkflows:   ()      => req('GET',    '/workflow/'),
  createWorkflow:  (data)  => req('POST',   '/workflow/', data),
  updateWorkflow:  (id, d) => req('PUT',    '/workflow/' + id, d),
  deleteWorkflow:  (id)    => req('DELETE', '/workflow/' + id),
  runWorkflow:     (id)    => req('POST',   '/workflow/' + id + '/run'),
  getWorkflowRuns: (id)    => req('GET',    '/workflow/' + id + '/runs'),

  // ── Analytics ────────────────────────────────────────────
  dashboard:      () => req('GET', '/analytics/dashboard'),
  usage:          () => req('GET', '/analytics/usage'),
  systemStats:    () => req('GET', '/analytics/system'),
  timeline:       () => req('GET', '/analytics/timeline'),
  resetAnalytics: () => req('DELETE', '/analytics/reset'),
  recentLogs:     (lines, level) => req('GET', '/analytics/logs/recent?lines=' + (lines||100) + (level ? '&level='+level : '')),
  storageInfo:    () => req('GET', '/analytics/storage'),
  cleanStorage:   (target) => req('POST', '/analytics/storage/clean?target=' + target),
  rotateLog:      () => req('POST', '/analytics/storage/rotate-log'),

  // ── Integrations ─────────────────────────────────────────
  integrationsStatus: () => req('GET', '/integrations/status'),

  // ── Webhooks ─────────────────────────────────────────────
  listWebhooks:     ()       => req('GET',    '/integrations/webhooks'),
  createWebhook:    (d)      => req('POST',   '/integrations/webhooks', d),
  updateWebhook:    (id, d)  => req('PUT',    '/integrations/webhooks/' + id, d),
  deleteWebhook:    (id)     => req('DELETE', '/integrations/webhooks/' + id),
  testWebhook:      (id)     => req('POST',   '/integrations/webhooks/' + id + '/test'),
  webhookTemplates: ()       => req('GET',    '/integrations/webhooks/templates'),

  // ── Security / Recovery ──────────────────────────────────
  generateRecoveryToken: (userId) => req('POST', '/security/recovery/generate' + (userId ? '?target_user_id=' + userId : '')),
  useRecoveryToken:      (token, pass, username) => req('POST', '/security/recovery/use?token=' + encodeURIComponent(token) + '&new_password=' + encodeURIComponent(pass) + (username ? '&username=' + encodeURIComponent(username) : '')),
  listRecoveryTokens:    () => req('GET', '/security/recovery/tokens'),
  emergencyReset:        (key, pass) => req('POST', '/security/recovery/emergency?emergency_key=' + encodeURIComponent(key) + '&new_password=' + encodeURIComponent(pass)),
  loginHistory:          () => req('GET', '/security/login-history'),
  clearLoginHistory:     () => req('DELETE', '/security/login-history'),
  loginLogs:             () => req('GET', '/security/login-history'),
  changePassword:        (cur, nw) => req('POST', '/security/change-password?current_password=' + encodeURIComponent(cur) + '&new_password=' + encodeURIComponent(nw)),

  // ── Email Reset (Auth2FA) ────────────────────────────────
  sendEmailReset:      (email) => req('POST', '/auth2fa/email/send-reset?email=' + encodeURIComponent(email)),
  resetPasswordEmail:  (token, pass) => req('POST', '/auth2fa/email/reset-password?token=' + encodeURIComponent(token) + '&new_password=' + encodeURIComponent(pass)),
  testSmtp:            () => req('POST', '/auth2fa/email/test-smtp'),
  smtpStatus:          () => req('GET',  '/auth2fa/email/smtp-status'),

  // ── Telegram OTP (Auth2FA) ───────────────────────────────
  setupTelegramOtp:    (chatId) => req('POST', '/auth2fa/telegram-otp/setup?telegram_chat_id=' + encodeURIComponent(chatId)),
  verifyTelegramSetup: (code)   => req('POST', '/auth2fa/telegram-otp/verify-setup?otp_code=' + encodeURIComponent(code)),
  sendTelegramOtp:     (uname)  => req('POST', '/auth2fa/telegram-otp/send?username=' + encodeURIComponent(uname)),
  sendTelegramReset:   (uname)  => req('POST', '/auth2fa/telegram-otp/send-reset?username=' + encodeURIComponent(uname)),
  checkTelegramSetup:  (uname)  => reqPublic('GET', '/auth2fa/telegram-otp/check/' + encodeURIComponent(uname)),
  telegramResetPass:   (uname, otp, pass_) => req('POST', '/auth2fa/telegram-otp/reset-password', { username: uname, otp_code: otp, new_password: pass_ }),
  verifyTelegramOtp:   (uname, code) => req('POST', '/auth2fa/telegram-otp/verify-login?username=' + encodeURIComponent(uname) + '&otp_code=' + encodeURIComponent(code)),

  // ── TOTP 2FA (Auth2FA) ────────────────────────────────────
  totpSetupStart:  ()            => req('POST', '/auth2fa/totp/setup/start'),
  totpSetupVerify: (code)        => req('POST', '/auth2fa/totp/setup/verify?code=' + encodeURIComponent(code)),
  totpDisable:     (pass, code)  => req('POST', '/auth2fa/totp/disable?password=' + encodeURIComponent(pass) + '&code=' + encodeURIComponent(code)),
  totpVerifyLogin: (uname, code) => req('POST', '/auth2fa/totp/verify-login?username=' + encodeURIComponent(uname) + '&code=' + encodeURIComponent(code)),
  totpStatus:      ()            => req('GET',  '/auth2fa/totp/status'),

  // ── Health ────────────────────────────────────────────────
  health: () => req('GET', '/health'),

  // ── Upload (multipart) ────────────────────────────────────
  uploadDoc: async function(file, collection) {
    collection = collection || 'default'
    const token = getToken()
    const form  = new FormData()
    form.append('file', file)
    form.append('collection', collection)
    const res = await fetch(BASE + '/rag/upload', {
      method:  'POST',
      headers: token ? { 'Authorization': 'Bearer ' + token } : {},
      body:    form,
    })
    if (!res.ok) throw new Error('Upload failed')
    return res.json()
  },

  // ── Streaming chat via SSE ────────────────────────────────
  chatStream: function(payload, onChunk, onDone, onSession, onPending, onStatus) {
    const token      = getToken()
    const controller = new AbortController()

    fetch(BASE + '/chat/send', {
      method:  'POST',
      headers: Object.assign(
        { 'Content-Type': 'application/json' },
        token ? { 'Authorization': 'Bearer ' + token } : {}
      ),
      body:   JSON.stringify(payload),
      signal: controller.signal,
    }).then(async function(res) {
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer    = ''

      while (true) {
        const chunk = await reader.read()
        if (chunk.done) break
        buffer += decoder.decode(chunk.value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'chunk')        onChunk(data.content)
              else if (data.type === 'done')    onDone(data)
              else if (data.type === 'session') onSession && onSession(data)
              else if (data.type === 'pending_confirmation') onPending && onPending(data)
              else if (data.type === 'status')  onStatus && onStatus(data.content)
            } catch(err) {}
          }
        }
      }
    }).catch(function(e) {
      if (e.name !== 'AbortError') console.error('Stream error', e)
    })

    return function() { controller.abort() }
  },

  executePending: function(payload, onChunk, onDone) {
    const token      = getToken()
    const controller = new AbortController()

    fetch(BASE + '/chat/execute_pending', {
      method:  'POST',
      headers: Object.assign(
        { 'Content-Type': 'application/json' },
        token ? { 'Authorization': 'Bearer ' + token } : {}
      ),
      body:   JSON.stringify(payload),
      signal: controller.signal,
    }).then(async function(res) {
      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer    = ''

      while (true) {
        const chunk = await reader.read()
        if (chunk.done) break
        buffer += decoder.decode(chunk.value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'chunk')        onChunk(data.content)
              else if (data.type === 'done')    onDone(data)
            } catch(err) {}
          }
        }
      }
    }).catch(function(e) {
      if (e.name !== 'AbortError') console.error('Stream error', e)
    })

    return function() { controller.abort() }
  },

  // RAG / Google Drive
  gdriveFolders:    ()  => req('GET',  '/rag/google-drive/folders'),
  gdriveSync:       (d) => req('POST', '/rag/google-drive/sync-folder', d),

  // ── Drive Manual Upload ──────────────────────────────────
  getDriveFolders: () => req('GET', '/drive/folders'),
  createDriveFolder: (d) => req('POST', '/drive/folders', d),
  uploadGeneratedToDrive: async function(content, format, filename, folder_id) {
    const token = getToken()
    const form = new FormData()
    form.append('content', content)
    form.append('format', format)
    form.append('filename', filename)
    if (folder_id) form.append('folder_id', folder_id)

    const res = await fetch(BASE + '/drive/upload_generated', {
      method: 'POST',
      headers: token ? { 'Authorization': 'Bearer ' + token } : {},
      body: form,
    })
    if (!res.ok) {
        const e = await res.json().catch(function() { return {} })
        throw new Error(e.detail || 'Upload failed')
    }
    return res.json()
  },
}
