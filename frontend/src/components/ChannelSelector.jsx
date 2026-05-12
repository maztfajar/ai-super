import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check, Globe, MessageCircle, Send, Radio } from 'lucide-react'
import clsx from 'clsx'
import { useOrchestratorStore } from '../store'
import { useTranslation } from 'react-i18next'

/**
 * Map channel type → Lucide icon for clean rendering alongside emoji.
 */
const CHANNEL_ICONS = {
  web:      Globe,
  whatsapp: MessageCircle,
  telegram: Send,
}

/**
 * ChannelSelector — Dropdown for selecting the active channel/session.
 * Reads `connectedChannels` and `selectedChannel` from the Zustand store.
 *
 * To connect to your backend later, replace the store's initial values
 * with an API fetch in a useEffect, e.g.:
 *   api.getConnectedChannels().then(setConnectedChannels)
 */
export default function ChannelSelector() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  const connectedChannels = useOrchestratorStore(s => s.connectedChannels)
  const selectedChannel   = useOrchestratorStore(s => s.selectedChannel)
  const setSelectedChannel = useOrchestratorStore(s => s.setSelectedChannel)

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  const currentChannel = connectedChannels.find(c => c.id === selectedChannel) || connectedChannels[0]
  const CurrentIcon = currentChannel ? (CHANNEL_ICONS[currentChannel.type] || Radio) : Radio

  const handleSelect = (id) => {
    setSelectedChannel(id)
    setOpen(false)
  }

  return (
    <div ref={ref} className="relative" id="channel-selector">
      {/* Trigger button */}
      <button
        onClick={() => setOpen(!open)}
        className={clsx(
          'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold transition-all border shadow-sm',
          'bg-bg-4 border-border-2 text-ink hover:bg-bg-5 hover:border-accent/40',
          open && 'border-accent/60 bg-bg-5 ring-1 ring-accent/20'
        )}
      >
        <CurrentIcon size={14} className="text-accent-2 flex-shrink-0" />
        <span className="truncate max-w-[150px] font-bold">
          {currentChannel?.name || t('select_channel')}
        </span>
        <ChevronDown
          size={14}
          className={clsx('text-ink-3 transition-transform duration-200', open && 'rotate-180')}
        />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-56 bg-bg-2 border border-border-2 rounded-xl shadow-2xl shadow-black/20 z-[100] overflow-hidden animate-fade">
          {/* Header */}
          <div className="px-3 pt-3 pb-2 border-b border-border/20 mb-1">
            <div className="text-xs font-bold tracking-widest uppercase text-ink-3 flex items-center gap-2">
              <Radio size={12} className="text-accent-2" />
              {t('channel_session')}
            </div>
          </div>

          {/* Options */}
          <div className="px-2 pb-2">
            {connectedChannels.length === 0 ? (
              <div className="px-2.5 py-2 text-xs text-ink-3 italic">
                {t('no_channels_connected')}
              </div>
            ) : (
              connectedChannels.map((ch) => {
                const Icon = CHANNEL_ICONS[ch.type] || Radio
                const isSelected = selectedChannel === ch.id
                return (
                  <button
                    key={ch.id}
                    onClick={() => handleSelect(ch.id)}
                    className={clsx(
                      'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all text-sm group',
                      isSelected
                        ? 'bg-accent/10 text-accent-2 font-semibold shadow-sm'
                        : 'text-ink hover:bg-bg-4 font-medium'
                    )}
                  >
                    <Icon size={16} className={clsx('flex-shrink-0', isSelected ? 'text-accent-2' : 'text-ink-3 group-hover:text-ink-2')} />
                    <span className="flex-1 truncate">{ch.name}</span>
                    {isSelected && <Check size={14} className="text-accent-2" />}
                    {ch.isDefault && !isSelected && (
                      <span className="text-[11px] text-ink-3 border border-border rounded px-2 py-0.5 font-semibold uppercase tracking-tight bg-bg-5">{t('main')}</span>
                    )}
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
