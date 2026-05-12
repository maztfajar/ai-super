import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, Bot, BookOpen, Brain,
  Repeat2, BarChart3, Plug, FlaskConical, ScrollText,
  Settings, Shield, Users, Activity, LogOut, Sun, Moon,
  User
} from 'lucide-react'
import { useAuthStore, useThemeStore } from '../store'
import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import clsx from 'clsx'
import './MinimalSidebar.css'

const NAV_GROUPS = [
  {
    title: 'section_utama',
    items: [
      { to: '/dashboard',   icon: LayoutDashboard, label: 'dashboard' },
      { to: '/chat',        icon: MessageSquare,   label: 'chat' },
      { to: '/models',      icon: Bot,             label: 'models' },
    ]
  },
  {
    title: 'section_data_ai',
    items: [
      { to: '/knowledge',   icon: BookOpen,        label: 'knowledge' },
      { to: '/memory',      icon: Brain,           label: 'memory' },
    ]
  },
  {
    title: 'section_otomasi',
    items: [
      { to: '/workflow',    icon: Repeat2,         label: 'workflow' },
      { to: '/integrations',icon: Plug,            label: 'integrations' },
    ]
  },
  {
    title: 'section_monitor',
    items: [
      { to: '/analytics',   icon: BarChart3,       label: 'analytics' },
      { to: '/monitoring',  icon: Activity,        label: 'monitoring_ai' },
      { to: '/logs',        icon: ScrollText,      label: 'logs' },
      { to: '/playground',  icon: FlaskConical,    label: 'playground' },
    ]
  },
  {
    title: 'section_keamanan',
    items: [
      { to: '/settings',    icon: Settings,        label: 'settings' },
      { to: '/security2fa', icon: Shield,          label: '2fa_login' },
      { to: '/admin',       icon: Users,           label: 'admin', adminOnly: true },
    ]
  }
]

export default function MinimalSidebar() {
  const { t } = useTranslation()
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const navigate = useNavigate()
  const isAdmin = user?.is_admin

  // Interactive hover expansion
  const [isCollapsed, setIsCollapsed] = useState(true)
  const [showUserMenu, setShowUserMenu] = useState(false)

  const handleMouseEnter = () => setIsCollapsed(false)
  const handleMouseLeave = () => {
    setIsCollapsed(true)
    setShowUserMenu(false) // Close menu when leaving sidebar
  }

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <aside 
      className={clsx("msb", isCollapsed && "msb--collapsed")}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Brand Header */}
      <div className="msb-header">
        <div className="msb-logo-wrap">
          <div className="msb-logo-icon">🧠</div>
          <div className="msb-logo-text">
            <div className="msb-logo-main">AI ORCHESTRATOR</div>
            <div className="msb-logo-sub">AI ORCHESTRATOR</div>
          </div>
        </div>
      </div>

      {/* Nav Content */}
      <div className="msb-content">
        {NAV_GROUPS.map((group) => {
          const visibleItems = group.items.filter(i => !i.adminOnly || isAdmin)
          if (visibleItems.length === 0) return null
          
          return (
            <div key={group.title} className="msb-group">
              {/* <div className="msb-group-title">{group.title}</div> */}
              {visibleItems.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  className={({ isActive }) => clsx('msb-item', isActive && 'msb-item--active')}
                >
                  <Icon size={18} strokeWidth={1.5} className="msb-item-icon" />
                  <span className="msb-item-label">{t(label)}</span>
                </NavLink>
              ))}
            </div>
          )
        })}
      </div>

      {/* User / Footer */}
      <div className="msb-footer">
        {/* Expanded User Menu */}
        <div className={clsx("msb-user-menu", showUserMenu && "msb-user-menu--open")}>
          <button className="msb-menu-item" onClick={() => navigate('/profile')}>
            <User size={16} />
            <span>{t('edit_profile')}</span>
          </button>
          <button className="msb-menu-item msb-menu-item--danger" onClick={handleLogout}>
            <LogOut size={16} />
            <span>{t('logout')}</span>
          </button>
        </div>

        <div className="msb-user" onClick={() => setShowUserMenu(!showUserMenu)} title={t('show_options')}>
          <div className="msb-user-avatar">
            {user?.username?.[0]?.toUpperCase() || 'A'}
          </div>
          <div className="msb-user-info">
            <div className="msb-user-name">{user?.username || 'admin'}</div>
            <div className="msb-user-action">
              <span>{showUserMenu ? t('hide_options') : t('show_options')}</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
