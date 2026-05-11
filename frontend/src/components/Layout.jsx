import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore, useUIStore, useThemeStore, useOrchestratorStore, useChatStore } from '../store'
import { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import { useTranslation } from 'react-i18next'
import MinimalSidebar from '../components/MinimalSidebar';
import ChatHistorySidebar from '../components/ChatHistorySidebar';
import {
  LayoutDashboard, MessageSquare, Bot, BookOpen, Brain, Repeat2,
  BarChart3, Plug, FlaskConical, ScrollText, Menu, LogOut, Settings,
  UserCircle, ShieldCheck, Users, Shield, ShieldAlert, Activity,
  Moon, Sun, X, ChevronLeft,
} from 'lucide-react'
import clsx from 'clsx'
import OrchestratorDropdown from './OrchestratorDropdown'
import ChannelSelector from './ChannelSelector'

import toast from 'react-hot-toast'

// ── Topbar New Chat Button dengan guard sesi kosong ─────────────
function TopbarNewChatButton() {
  const navigate = useNavigate()
  const location = useLocation()
  const currentSession = useChatStore(s => s.currentSession)
  const messages = useChatStore(s => s.messages)

  const isOnChatPage = location.pathname.startsWith('/chat')
  const isCurrentSessionEmpty = currentSession && messages.length === 0

  const handleClick = () => {
    if (isCurrentSessionEmpty) {
      toast('Sesi ini masih kosong. Mulai chat dulu!', { icon: '💬', duration: 2000 })
      return
    }
    useChatStore.getState().setCurrentSession(null)
    useChatStore.getState().clearMessages()
    navigate('/chat', { replace: true })
  }

  return (
    <button
      onClick={handleClick}
      disabled={isCurrentSessionEmpty}
      title={isCurrentSessionEmpty ? 'Sesi ini masih kosong, mulai chat dulu!' : 'Buat sesi chat baru'}
      className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent hover:bg-accent/80 text-white text-[10px] font-bold uppercase tracking-widest transition-all shadow-lg shadow-accent/20 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed border-2 border-accent-2/20"
    >
      <MessageSquare size={16}/>New Chat
    </button>
  )
}

export default function Layout() {
  const { t } = useTranslation()
  const { user, logout } = useAuthStore()
  const { sidebarOpen, toggleSidebar } = useUIStore()
  const navigate  = useNavigate()
  const location  = useLocation()
  
  // Mobile responsive state
  const [isMobile, setIsMobile] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  
  // Detect mobile screen size
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
      // Auto-close sidebar on mobile
      if (window.innerWidth < 768 && sidebarOpen) {
        toggleSidebar()
      }
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [sidebarOpen, toggleSidebar])
  
  // Close mobile menu when route changes
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [location.pathname])

  const NAV_ADMIN = [
    { label: t('dashboard'),        to: '/dashboard',    icon: LayoutDashboard, section: 'Utama' },
    { label: t('chat'),             to: '/chat',         icon: MessageSquare,   section: 'Utama' },
    { label: t('models'),           to: '/models',       icon: Bot,             section: 'Utama' },
    { label: t('knowledge'),        to: '/knowledge',    icon: BookOpen,        section: 'Data & AI' },
    { label: t('memory'),           to: '/memory',       icon: Brain,           section: 'Data & AI' },
    { label: t('workflow'),         to: '/workflow',     icon: Repeat2,         section: 'Otomasi' },
    { label: t('integrations'),     to: '/integrations', icon: Plug,            section: 'Otomasi' },
    { label: t('analytics'),        to: '/analytics',    icon: BarChart3,       section: 'Monitor' },
    { label: t('monitoring_ai'),    to: '/monitoring',   icon: Activity,        section: 'Monitor' },
    { label: t('logs'),             to: '/logs',         icon: ScrollText,      section: 'Monitor' },
    { label: t('playground'),       to: '/playground',   icon: FlaskConical,    section: 'Monitor' },
    { label: t('settings'),         to: '/settings',     icon: Settings,        section: 'Keamanan' },
    { label: t('2fa_login'),        to: '/security2fa',  icon: Shield,          section: 'Keamanan' },
    { label: t('admin'),            to: '/admin',        icon: Users,           section: 'Keamanan' },
  ]

  const NAV_SUBADMIN = [
    { label: t('dashboard'),        to: '/dashboard',    icon: LayoutDashboard, section: 'Utama' },
    { label: t('chat'),             to: '/chat',         icon: MessageSquare,   section: 'Utama' },
    { label: t('analytics'),        to: '/analytics',    icon: BarChart3,       section: 'Monitor' },
    { label: t('2fa_login'),        to: '/security2fa',  icon: Shield,          section: 'Keamanan' },
  ]

  const appName = useOrchestratorStore(s => s.appName)
  const setAppName = useOrchestratorStore(s => s.setAppName)
  const [logoUrl, setLogoUrl]       = useState('')
  const [showMenu, setShowMenu]     = useState(false)

  const selectedOrchestrator    = useOrchestratorStore(s => s.selectedOrchestrator)
  const setSelectedOrchestrator = useOrchestratorStore(s => s.setSelectedOrchestrator)

  const { theme, toggleTheme } = useThemeStore()
  const isAdmin = user?.is_admin
  const NAV     = isAdmin ? NAV_ADMIN : NAV_SUBADMIN
  
  // Extract unique sections from NAV in order
  const SECTIONS = Array.from(new Set(NAV.map(n => n.section)))
  
  // Section header translations map
  const sectionLabels = {
    'Utama': t('section_utama'),
    'Data & AI': t('section_data_ai'),
    'Otomasi': t('section_otomasi'),
    'Monitor': t('section_monitor'),
    'Keamanan': t('section_keamanan'),
  }

  // Sync app profile + models on mount
  useEffect(() => {
    const load = () => {
      api.getAppProfile().then(p => {
        if (p && p.app_name) setAppName(p.app_name)
        if (p && p.logo_url) setLogoUrl(p.logo_url + '?t=' + Date.now())
      }).catch(() => {})
    }
    load()
    window.addEventListener('ai-orchestrator:profile-updated', load)

    // Fetch models and sync to orchestrator store so dropdowns have data on first load
    const setActiveConfiguredModels = useOrchestratorStore.getState().setActiveConfiguredModels
    api.listModels().then(r => {
      const ms = r?.models || []
      if (ms.length > 0) {
        const mapped = ms.map(m => ({
          id: m.id,
          name: `🧠 ${m.display || m.id}`,
          provider: (m.provider || 'unknown').charAt(0).toUpperCase() + (m.provider || 'unknown').slice(1),
        }))
        setActiveConfiguredModels(mapped)
      }
    }).catch(() => {})

    return () => window.removeEventListener('ai-orchestrator:profile-updated', load)
  }, [setAppName])

  useEffect(() => {
    if (!isAdmin) {
      const allowed = ['/dashboard', '/chat', '/analytics', '/profile', '/security2fa']
      const ok = allowed.some(p => location.pathname.startsWith(p))
      if (!ok) navigate('/dashboard', { replace: true })
    }
  }, [location.pathname, isAdmin])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex h-[100dvh] bg-bg overflow-hidden">
      <MinimalSidebar />

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className={clsx(
          'border-b-2 border-border bg-bg-2 flex items-center justify-between flex-shrink-0 z-50',
          // Mobile: taller header with better spacing
          isMobile ? 'h-14 px-3' : 'h-14 px-6'
        )}>
          <div className="flex items-center gap-3">
            {isMobile && (
              <button onClick={() => setMobileMenuOpen(true)} className="p-2 rounded-xl hover:bg-bg-4 text-ink-2 hover:text-ink transition-all shadow-sm">
                <Menu size={20}/>
              </button>
            )}
            <div className="flex items-center gap-3 min-w-0">
              <span className="w-2.5 h-2.5 rounded-full bg-success animate-pulse2 flex-shrink-0 shadow-[0_0_10px_rgba(34,197,94,0.5)]"/>
              <span className={clsx('text-ink-3 truncate font-bold uppercase tracking-tight', isMobile ? 'text-xs' : 'text-sm')}>{appName}</span>
            </div>
          </div>
          
          <div className={clsx('flex items-center gap-2', isMobile ? 'gap-1.5' : 'gap-2')}>
            {/* Mobile: Compact layout */}
            {isMobile ? (
              <>
                <OrchestratorDropdown
                  value={selectedOrchestrator}
                  onChange={setSelectedOrchestrator}
                  compact={true}
                />
                <button onClick={toggleTheme} title={theme === 'dark' ? 'Mode Terang' : 'Mode Gelap'}
                  className="p-1.5 rounded-lg hover:bg-bg-4 text-ink-2 hover:text-ink transition-colors">
                  {theme === 'dark' ? <Sun size={15}/> : <Moon size={15}/>}
                </button>
                <TopbarNewChatButton />
              </>
            ) : (
              /* Desktop: Full layout */
              <>
                <OrchestratorDropdown
                  value={selectedOrchestrator}
                  onChange={setSelectedOrchestrator}
                />
                <div className="w-px h-6 bg-border opacity-50" />
                <ChannelSelector />
                <div className="w-px h-6 bg-border opacity-50" />
                <button onClick={toggleTheme} title={theme === 'dark' ? 'Mode Terang' : 'Mode Gelap'}
                  className="p-2 rounded-xl hover:bg-bg-4 text-ink-2 hover:text-ink transition-all shadow-sm">
                  {theme === 'dark' ? <Sun size={18}/> : <Moon size={18}/>}
                </button>
                <TopbarNewChatButton />
              </>
            )}
          </div>
        </header>
        <main className={clsx("flex-1 flex overflow-hidden", isMobile && "pb-14")}>
          {!isMobile && location.pathname.startsWith('/chat') && (
            <ChatHistorySidebar />
          )}
          <div className="flex-1 overflow-auto">
            <Outlet/>
          </div>
        </main>
      </div>

      {/* Mobile Bottom Navigation */}
      {isMobile && (
        <div className="fixed bottom-0 left-0 right-0 h-16 bg-bg border-t-2 border-border flex items-center justify-around z-50 px-2 pb-safe shadow-[0_-10px_40px_rgba(0,0,0,0.2)]">
          <NavLink to="/dashboard" className={({isActive}) => clsx("flex flex-col items-center justify-center w-full h-full gap-2", isActive ? "text-accent-2" : "text-ink-3 hover:text-ink")}>
            <LayoutDashboard size={26} />
            <span className="text-xs font-bold uppercase tracking-tight">Utama</span>
          </NavLink>
          <NavLink to="/chat" className={({isActive}) => clsx("flex flex-col items-center justify-center w-full h-full gap-2", isActive ? "text-accent-2" : "text-ink-3 hover:text-ink")}>
            <MessageSquare size={26} />
            <span className="text-xs font-bold uppercase tracking-tight">Chat</span>
          </NavLink>
          {isAdmin && (
            <NavLink to="/integrations" className={({isActive}) => clsx("flex flex-col items-center justify-center w-full h-full gap-2", isActive ? "text-accent-2" : "text-ink-3 hover:text-ink")}>
              <Plug size={26} />
              <span className="text-xs font-bold uppercase tracking-tight">Integrasi</span>
            </NavLink>
          )}
          <NavLink to="/analytics" className={({isActive}) => clsx("flex flex-col items-center justify-center w-full h-full gap-2", isActive ? "text-accent-2" : "text-ink-3 hover:text-ink")}>
            <BarChart3 size={26} />
            <span className="text-xs font-bold uppercase tracking-tight">Statistik</span>
          </NavLink>
          <button onClick={() => setMobileMenuOpen(true)} className={clsx("flex flex-col items-center justify-center w-full h-full gap-2", mobileMenuOpen ? "text-accent-2" : "text-ink-3 hover:text-ink")}>
            <Menu size={26} />
            <span className="text-xs font-bold uppercase tracking-tight">Menu</span>
          </button>
        </div>
      )}

      {/* Mobile Bottom Sheet Menu */}
      {isMobile && mobileMenuOpen && (
        <>
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[60] animate-fade" onClick={() => setMobileMenuOpen(false)} />
          <div className="fixed bottom-0 left-0 right-0 bg-bg-2 border-t-2 border-border rounded-t-3xl z-[70] animate-slide-in-up max-h-[85vh] flex flex-col shadow-[0_-20px_60px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="p-6 border-b-2 border-border flex items-center justify-between bg-bg-3 shadow-sm">
              <span className="text-lg font-bold text-ink uppercase tracking-tight">Menu Utama</span>
              <button onClick={() => setMobileMenuOpen(false)} className="p-2 rounded-xl bg-bg-4 text-ink-3 hover:text-ink transition-all shadow-sm">
                <X size={20} />
              </button>
            </div>
            <div className="overflow-y-auto p-2 pb-6">
              <div className="flex items-center gap-3 px-3 py-3 mb-2 border-b border-border/50">
                <div className={clsx('w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0', isAdmin ? 'bg-gradient-to-br from-accent to-pink text-white' : 'bg-bg-4 text-ink-2 border border-border')}>
                  {user?.username?.[0]?.toUpperCase() || 'A'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-base font-semibold text-ink truncate">{user?.username}</div>
                  <div className="text-sm text-ink-3 font-medium">{isAdmin ? '👑 Admin' : '👤 Sub Admin'}</div>
                </div>
                <NavLink to="/profile" onClick={() => setMobileMenuOpen(false)} className="p-2 rounded-lg bg-bg-4 text-ink-3 hover:text-ink">
                  <Settings size={16} />
                </NavLink>
              </div>

              {SECTIONS.map(section => {
                const items = NAV.filter(n => n.section === section);
                if (!items.length) return null;
                // Skip rendering items that are already on bottom nav
                const filteredItems = items.filter(i => !['/dashboard', '/chat', '/integrations', '/analytics'].includes(i.to));
                if (!filteredItems.length) return null;

                return (
                  <div key={section} className="mb-6">
                    <div className="text-[10px] font-bold tracking-widest uppercase text-accent-2 px-5 mb-3 opacity-80">
                      {sectionLabels[section]}
                    </div>
                    {filteredItems.map(({ label, to, icon: Icon }) => (
                      <NavLink 
                        key={to} 
                        to={to}
                        onClick={() => setMobileMenuOpen(false)}
                        className={({ isActive }) => clsx(
                          'flex items-center gap-4 px-4 py-4 rounded-2xl mb-1.5 text-[15px] transition-all',
                          isActive ? 'bg-accent/10 text-accent-2 font-semibold' : 'text-ink-2 hover:bg-bg-4 hover:text-ink'
                        )}>
                        <Icon size={22} />
                        <span>{label}</span>
                      </NavLink>
                    ))}
                  </div>
                )
              })}
              
              <div className="border-t-2 border-border mt-2 pt-4 px-4 pb-8">
                <button onClick={handleLogout} className="w-full flex items-center gap-4 px-6 py-5 rounded-2xl text-lg font-bold text-danger bg-danger/5 hover:bg-danger/10 transition-all shadow-sm">
                  <LogOut size={24} /> {t('logout')}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
