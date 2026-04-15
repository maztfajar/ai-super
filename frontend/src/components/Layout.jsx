import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore, useUIStore, useThemeStore, useOrchestratorStore } from '../store'
import { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard, MessageSquare, Bot, BookOpen, Brain, Repeat2,
  BarChart3, Plug, FlaskConical, ScrollText, Menu, LogOut, Settings,
  UserCircle, ShieldCheck, Users, Shield, ShieldAlert, Activity,
  Moon, Sun,
} from 'lucide-react'
import clsx from 'clsx'
import OrchestratorDropdown from './OrchestratorDropdown'
import ChannelSelector from './ChannelSelector'

export default function Layout() {
  const { t } = useTranslation()
  const { user, logout } = useAuthStore()
  const { sidebarOpen, toggleSidebar } = useUIStore()
  const navigate  = useNavigate()
  const location  = useLocation()

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
      <aside className={clsx(
        'flex flex-col bg-bg-2 border-r border-border transition-all duration-200 flex-shrink-0',
        sidebarOpen ? 'w-52' : 'w-14'
      )}>
        {/* Logo */}
        <div className="flex items-center gap-2.5 px-3.5 py-4 border-b border-border">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center flex-shrink-0 shadow-lg shadow-accent/20 overflow-hidden">
            {logoUrl ? <img src={logoUrl} alt="logo" className="w-full h-full object-contain"/> : <span className="text-sm font-bold">🧠</span>}
          </div>
          {sidebarOpen && (
            <div className="min-w-0">
              <div className="text-sm font-bold tracking-wide text-ink truncate">{appName}</div>
              <div className="text-[9px] text-ink-3 tracking-widest uppercase">AI Orchestrator</div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2 px-2">
          {SECTIONS.map(section => {
            const items = NAV.filter(n => n.section === section)
            if (!items.length) return null
            return (
              <div key={section} className="mb-1">
                {sidebarOpen && (
                  <div className="text-[9px] font-semibold tracking-widest uppercase text-ink-3 px-2 pt-3 pb-1">
                    {sectionLabels[section]}
                  </div>
                )}
                {!sidebarOpen && section !== 'Utama' && items.length > 0 && (
                  <div className="border-t border-border/50 my-1 mx-2"/>
                )}
                {items.map(({ label, to, icon: Icon }) => (
                  <NavLink key={to} to={to}
                    className={({ isActive }) => clsx(
                      'flex items-center gap-2.5 px-2.5 py-2 rounded-lg mb-0.5 text-sm transition-all relative group',
                      isActive ? 'bg-accent/10 text-accent-2 font-medium' : 'text-ink-2 hover:bg-bg-4 hover:text-ink'
                    )}>
                    {({ isActive }) => (
                      <>
                        {isActive && <span className="absolute left-0 top-1/4 bottom-1/4 w-0.5 bg-accent rounded-r"/>}
                        <Icon size={15} className="flex-shrink-0"/>
                        {sidebarOpen && <span>{label}</span>}
                        {!sidebarOpen && (
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
              {sidebarOpen && (
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
                sidebarOpen ? 'left-0 right-0' : 'left-full ml-2 w-40'
              )}>
                <NavLink to="/profile" onClick={() => setShowMenu(false)}
                  className="flex items-center gap-2.5 px-3 py-2.5 text-xs text-ink-2 hover:bg-bg-4 hover:text-ink transition-colors">
                  <UserCircle size={13}/>Edit Profil
                </NavLink>
                <NavLink to="/security2fa" onClick={() => setShowMenu(false)}
                  className="flex items-center gap-2.5 px-3 py-2.5 text-xs text-ink-2 hover:bg-bg-4 hover:text-ink transition-colors">
                  <Shield size={13}/>2FA & Keamanan
                </NavLink>
                {isAdmin && (
                  <NavLink to="/admin" onClick={() => setShowMenu(false)}
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
        <header className="h-12 border-b border-border bg-bg-2 flex items-center px-4 gap-3 flex-shrink-0">
          <button onClick={toggleSidebar} className="p-1.5 rounded-lg hover:bg-bg-4 text-ink-2 hover:text-ink transition-colors">
            <Menu size={16}/>
          </button>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse2"/>
            <span className="text-xs text-ink-3">{appName}</span>
          </div>
          <div className="ml-auto flex items-center gap-2">
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
            <NavLink to="/chat" className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent hover:bg-accent/80 text-white text-xs font-medium transition-colors">
              <MessageSquare size={12}/>New Chat
            </NavLink>
          </div>
        </header>
        <main className="flex-1 overflow-auto">
          <Outlet/>
        </main>
      </div>
    </div>
  )
}
