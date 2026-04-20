import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore, useUIStore, useThemeStore, useOrchestratorStore, useChatStore } from '../store'
import { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import { useTranslation } from 'react-i18next'
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
    navigate('/chat')
  }

  return (
    <button
      onClick={handleClick}
      disabled={isCurrentSessionEmpty}
      title={isCurrentSessionEmpty ? 'Sesi ini masih kosong, mulai chat dulu!' : 'Buat sesi chat baru'}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent hover:bg-accent/80 text-white text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
    >
      <MessageSquare size={12}/>New Chat
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
    window.addEventListener('ai-super-assistant:profile-updated', load)

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

    return () => window.removeEventListener('ai-super-assistant:profile-updated', load)
  }, [setAppName])

  useEffect(() => {
    if (!isAdmin) {
      const allowed = ['/dashboard', '/chat', '/analytics', '/profile', '/security2fa']
      const ok = allowed.some(p => location.pathname.startsWith(p))
      if (!ok) navigate('/dashboard', { replace: true })
    }
  }, [location.pathname, isAdmin])

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="flex h-screen bg-bg overflow-hidden">
      {/* Mobile overlay */}
      {isMobile && mobileMenuOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      
      <aside className={clsx(
        'flex flex-col bg-bg-2 border-r border-border transition-all duration-200 flex-shrink-0 z-50',
        // Mobile styles
        isMobile ? (mobileMenuOpen ? 'fixed left-0 top-0 h-full w-64' : 'hidden') :
        // Desktop styles
        (sidebarOpen ? 'w-52' : 'w-14')
      )}>
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-3.5 py-4 border-b border-border">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center flex-shrink-0 shadow-lg shadow-accent/20 overflow-hidden">
            {logoUrl ? <img src={logoUrl} alt="logo" className="w-full h-full object-contain"/> : <span className="text-sm font-bold">🧠</span>}
          </div>
          {(sidebarOpen || (isMobile && mobileMenuOpen)) && (
            <div className="min-w-0 flex-1">
              <div className="text-sm font-bold tracking-wide text-ink truncate">{appName}</div>
              <div className="text-[9px] text-ink-3 tracking-widest uppercase">AI Orchestrator</div>
            </div>
          )}
          {isMobile && mobileMenuOpen && (
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="p-1 rounded-lg hover:bg-bg-4 text-ink-2 transition-colors"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2 px-2">
          {SECTIONS.map(section => {
            const items = NAV.filter(n => n.section === section)
            if (!items.length) return null
            return (
              <div key={section} className="mb-1">
                {(sidebarOpen || (isMobile && mobileMenuOpen)) && (
                  <div className="text-[9px] font-semibold tracking-widest uppercase text-ink-3 px-2 pt-3 pb-1">
                    {sectionLabels[section]}
                  </div>
                )}
                {!sidebarOpen && !isMobile && section !== 'Utama' && items.length > 0 && (
                  <div className="border-t border-border/50 my-1 mx-2"/>
                )}
                {items.map(({ label, to, icon: Icon }) => (
                  <NavLink 
                    key={to} 
                    to={to}
                    onClick={() => isMobile && setMobileMenuOpen(false)}
                    className={({ isActive }) => clsx(
                      'flex items-center gap-2.5 px-2.5 py-2 rounded-lg mb-0.5 text-sm transition-all relative group',
                      isActive ? 'bg-accent/10 text-accent-2 font-medium' : 'text-ink-2 hover:bg-bg-4 hover:text-ink'
                    )}>
                    {({ isActive }) => (
                      <>
                        {isActive && <span className="absolute left-0 top-1/4 bottom-1/4 w-0.5 bg-accent rounded-r"/>}
                        <Icon size={15} className="flex-shrink-0"/>
                        {(sidebarOpen || (isMobile && mobileMenuOpen)) && <span className={clsx('text-sm', isMobile && 'text-base')}>{label}</span>}
                        {!sidebarOpen && !isMobile && (
                          <div className="absolute left-full ml-2 px-2 py-1 bg-bg-4 border border-border rounded text-xs text-ink whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none z-50 transition-opacity">
                            {label}
                          </div>
                        )}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            )
          })}
        </nav>

        {/* User footer */}
        <div className="border-t border-border p-2">
          <div className="relative">
            <button onClick={() => setShowMenu(!showMenu)}
              className="w-full flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-bg-4 transition-colors group">
              <div className={clsx('w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0',
                isAdmin ? 'bg-gradient-to-br from-accent to-pink text-white' : 'bg-bg-4 text-ink-2 border border-border')}>
                {user?.username?.[0]?.toUpperCase() || 'A'}
              </div>
              {(sidebarOpen || (isMobile && mobileMenuOpen)) && (
                <div className="flex-1 min-w-0 text-left">
                  <div className="text-xs font-medium text-ink truncate">{user?.username}</div>
                  <div className="text-[10px] text-ink-3 group-hover:text-accent-2 transition-colors">
                    {isAdmin ? '👑 Admin' : '👤 Sub Admin'} · <span className="group-hover:underline">Edit Profil</span>
                  </div>
                </div>
              )}
            </button>

            {showMenu && (
              <div className={clsx(
                'absolute bottom-full mb-1 bg-bg-3 border border-border rounded-xl shadow-xl overflow-hidden z-50',
                // Mobile: full width from sidebar, Desktop: position based on sidebar state
                isMobile ? 'left-0 right-0' : (sidebarOpen ? 'left-0 right-0' : 'left-full ml-2 w-40')
              )}>
                <NavLink to="/profile" onClick={() => {setShowMenu(false); isMobile && setMobileMenuOpen(false)}}
                  className="flex items-center gap-2.5 px-3 py-2.5 text-xs text-ink-2 hover:bg-bg-4 hover:text-ink transition-colors">
                  <UserCircle size={13}/>Edit Profil
                </NavLink>
                <NavLink to="/security2fa" onClick={() => {setShowMenu(false); isMobile && setMobileMenuOpen(false)}}
                  className="flex items-center gap-2.5 px-3 py-2.5 text-xs text-ink-2 hover:bg-bg-4 hover:text-ink transition-colors">
                  <Shield size={13}/>2FA & Keamanan
                </NavLink>
                {isAdmin && (
                  <NavLink to="/admin" onClick={() => {setShowMenu(false); isMobile && setMobileMenuOpen(false)}}
                    className="flex items-center gap-2.5 px-3 py-2.5 text-xs text-ink-2 hover:bg-bg-4 hover:text-ink transition-colors">
                    <ShieldCheck size={13}/>{t('admin')}
                  </NavLink>
                )}
                <div className="border-t border-border"/>
                <button onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs text-danger hover:bg-danger/10 transition-colors">
                  <LogOut size={13}/>{t('logout')}
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className={clsx(
          'border-b border-border bg-bg-2 flex items-center gap-3 flex-shrink-0',
          // Mobile: taller header with better spacing
          isMobile ? 'h-14 px-3' : 'h-12 px-4'
        )}>
          {/* Mobile menu toggle */}
          {isMobile ? (
            <button 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)} 
              className="p-2 rounded-lg hover:bg-bg-4 text-ink-2 hover:text-ink transition-colors"
            >
              {mobileMenuOpen ? <X size={18}/> : <Menu size={18}/>}
            </button>
          ) : (
            <button onClick={toggleSidebar} className="p-1.5 rounded-lg hover:bg-bg-4 text-ink-2 hover:text-ink transition-colors">
              {sidebarOpen ? <ChevronLeft size={16}/> : <Menu size={16}/>}
            </button>
          )}
          
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse2 flex-shrink-0"/>
            <span className={clsx('text-ink-3 truncate', isMobile ? 'text-xs' : 'text-xs')}>{appName}</span>
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
                <div className="w-px h-5 bg-border" />
                <ChannelSelector />
                <div className="w-px h-5 bg-border" />
                <button onClick={toggleTheme} title={theme === 'dark' ? 'Mode Terang' : 'Mode Gelap'}
                  className="p-1.5 rounded-lg hover:bg-bg-4 text-ink-2 hover:text-ink transition-colors">
                  {theme === 'dark' ? <Sun size={15}/> : <Moon size={15}/>}
                </button>
                <TopbarNewChatButton />
              </>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-auto">
          <Outlet/>
        </main>
      </div>
    </div>
  )
}
