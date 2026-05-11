import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, Bot, BookOpen, Brain,
  Repeat2, BarChart3, Plug, FlaskConical, ScrollText,
  Settings, Shield, Users, Activity, LogOut, Sun, Moon,
  User
} from 'lucide-react'
import { useAuthStore, useThemeStore } from '../store'
import { useState, useRef } from 'react'
import clsx from 'clsx'
import './MinimalSidebar.css'

const NAV_GROUPS = [
  {
    title: 'MAIN',
    items: [
      { to: '/dashboard',   icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/chat',        icon: MessageSquare,   label: 'Chat' },
      { to: '/models',      icon: Bot,             label: 'AI Models' },
    ]
  },
  {
    title: 'DATA & AI',
    items: [
      { to: '/knowledge',   icon: BookOpen,        label: 'Knowledge' },
      { to: '/memory',      icon: Brain,           label: 'Memory' },
    ]
  },
  {
    title: 'AUTOMATION',
    items: [
      { to: '/workflow',    icon: Repeat2,         label: 'Workflow' },
      { to: '/integrations',icon: Plug,            label: 'Integrations' },
    ]
  },
  {
    title: 'MONITOR',
    items: [
      { to: '/analytics',   icon: BarChart3,       label: 'Analytics' },
      { to: '/monitoring',  icon: Activity,        label: 'Monitoring AI' },
      { to: '/logs',        icon: ScrollText,      label: 'Logs' },
      { to: '/playground',  icon: FlaskConical,    label: 'Playground' },
    ]
  },
  {
    title: 'SECURITY',
    items: [
      { to: '/settings',    icon: Settings,        label: 'Settings' },
      { to: '/security2fa', icon: Shield,          label: '2FA & Login' },
      { to: '/admin',       icon: Users,           label: 'Admin', adminOnly: true },
    ]
  }
]

export default function MinimalSidebar() {
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
                  <span className="msb-item-label">{label}</span>
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
            <span>Edit Profile</span>
          </button>
          <button className="msb-menu-item msb-menu-item--danger" onClick={handleLogout}>
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>

        <div className="msb-user" onClick={() => setShowUserMenu(!showUserMenu)} title="Options">
          <div className="msb-user-avatar">
            {user?.username?.[0]?.toUpperCase() || 'A'}
          </div>
          <div className="msb-user-info">
            <div className="msb-user-name">{user?.username || 'admin'}</div>
            <div className="msb-user-action">
              <span>{showUserMenu ? 'Hide Options' : 'Show Options'}</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
  )
}
