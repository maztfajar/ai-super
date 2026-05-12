import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { MessageSquare, Plus, Trash2, Search } from 'lucide-react'
import { useChatStore } from '../store'
import clsx from 'clsx'
import { api } from '../hooks/useApi'
import { useTranslation } from 'react-i18next'
import './ChatHistorySidebar.css'

const NEON_COLORS = ['neon-success', 'neon-sky', 'neon-accent']

export default function ChatHistorySidebar() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [search, setSearch] = useState('')

  const sessions     = useChatStore(s => s.sessions || [])
  const currentSession = useChatStore(s => s.currentSession)
  const messages     = useChatStore(s => s.messages)

  // Filter sessions by search query
  const filtered = sessions.filter(s =>
    (s.title || s.id || '').toLowerCase().includes(search.toLowerCase())
  )

  const handleNew = () => {
    if (currentSession && messages.length === 0) return
    useChatStore.getState().setCurrentSession(null)
    useChatStore.getState().clearMessages?.()
    navigate('/chat', { replace: true })
  }

  const handleSelect = (session) => {
    navigate(`/chat/${session.id}`)
  }

  const handleDelete = async (e, sessionId) => {
    e.stopPropagation()
    if (!window.confirm(t('confirm_delete_chat'))) return

    // Optimistic UI update
    const prevSessions = useChatStore.getState().sessions
    const filtered = prevSessions.filter(s => s.id !== sessionId)
    useChatStore.getState().setSessions(filtered)
    
    const wasActive = currentSession?.id === sessionId
    if (wasActive) {
      useChatStore.getState().setCurrentSession(null)
      useChatStore.getState().clearMessages?.()
      navigate('/chat', { replace: true })
    }

    try {
      await api.deleteSession(sessionId)
      const updated = await api.listSessions()
      useChatStore.getState().setSessions(updated)
    } catch (err) {
      console.error(err)
      useChatStore.getState().setSessions(prevSessions)
      if (wasActive) {
        useChatStore.getState().setCurrentSession(prevSessions.find(s => s.id === sessionId) || null)
      }
      alert(t('error_delete_chat'))
    }
  }

  // Relative time helper
  const relativeTime = (ts) => {
    if (!ts) return ''
    const diff = Date.now() - new Date(ts).getTime()
    const m = Math.floor(diff / 60000)
    if (m < 1)  return 'Just now'
    if (m < 60) return `${m}m ago`
    const h = Math.floor(m / 60)
    if (h < 24) return `${h}h ago`
    return `${Math.floor(h / 24)}d ago`
  }

  return (
    <aside className="chsb">
      {/* Header */}
      <div className="chsb-header">
        <span className="chsb-title">
          <MessageSquare size={16} />
          {t('conversations')}
        </span>
        <button
          className="chsb-new-btn"
          onClick={handleNew}
          title={t('new_chat')}
        >
          <Plus size={18} />
        </button>
      </div>

      {/* Search */}
      <div className="chsb-search-wrap">
        <Search size={14} className="chsb-search-icon" />
        <input
          className="chsb-search"
          placeholder={t('search_placeholder')}
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      {/* Session list */}
      <div className="chsb-list">
        {filtered.length === 0 ? (
          <div className="chsb-empty">
            <MessageSquare size={28} className="chsb-empty-icon" />
            <p>{t('no_conversations')}</p>
            <p>{t('start_new_chat')}</p>
          </div>
        ) : (
          filtered.map((session, idx) => {
            const isActive = currentSession?.id === session.id ||
              location.pathname === `/chat/${session.id}`
            const neonClass = NEON_COLORS[idx % NEON_COLORS.length]
            return (
              <button
                key={session.id}
                onClick={() => handleSelect(session)}
                className={clsx('chsb-item', neonClass, isActive && 'chsb-item--active')}
              >
                <div className="chsb-item-body">
                  <span className="chsb-item-title">
                    {session.title || t('new_conversation')}
                  </span>
                  <span className="chsb-item-time">
                    {relativeTime(session.updated_at || session.created_at)}
                  </span>
                </div>
                <button
                  className="chsb-delete"
                  onClick={e => handleDelete(e, session.id)}
                  title={t('delete')}
                >
                  <Trash2 size={14} />
                </button>
              </button>
            )
          })
        )}
      </div>
    </aside>
  )
}
