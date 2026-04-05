import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore, useModelsStore, useOrchestratorStore } from './store'
import { api } from './hooks/useApi'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Models from './pages/Models'
import Knowledge from './pages/Knowledge'
import Memory from './pages/Memory'
import Workflow from './pages/Workflow'
import Analytics from './pages/Analytics'
import Integrations from './pages/Integrations'
import Playground from './pages/Playground'
import Logs from './pages/Logs'
import SettingsPage from './pages/Settings'
import Profile from './pages/Profile'
import Admin from './pages/Admin'
import Security2FA from './pages/Security2FA'

function Protected({ children }) {
  const token = useAuthStore(s => s.token)
  if (!token) return <Navigate to="/login" replace/>
  return children
}

function AdminOnly({ children }) {
  const user = useAuthStore(s => s.user)
  if (!user?.is_admin) return <Navigate to="/dashboard" replace/>
  return children
}

/**
 * Centralized model detection — runs at app-level so models are always
 * available regardless of which page is visited first.
 * Fixes: "Belum ada model aktif" intermittent issue (Bug #1).
 */
function useModelSync() {
  const token = useAuthStore(s => s.token)

  useEffect(() => {
    if (!token) return // not logged in yet

    const fetchAndSync = async () => {
      try {
        const r = await api.listModels()
        const ms = r.models || []
        useModelsStore.setState({ models: ms })
        // Sync to orchestrator store for dropdown
        const mapped = ms.map(m => ({
          id: m.id,
          name: `🧠 ${m.display || m.id}`,
          provider: (m.provider || 'unknown').charAt(0).toUpperCase() + (m.provider || 'unknown').slice(1),
        }))
        useOrchestratorStore.getState().setActiveConfiguredModels(mapped)
      } catch {
        // Silent fail — models will be retried on next interval
      }
    }

    fetchAndSync()
    const interval = setInterval(fetchAndSync, 60_000) // refresh every 60s
    return () => clearInterval(interval)
  }, [token])
}

export default function App() {
  useModelSync()

  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{
        style: { background: '#16181f', color: '#d4d8f0', border: '1px solid rgba(100,120,255,0.2)' },
      }}/>
      <Routes>
        <Route path="/login" element={<Login/>}/>
        <Route path="/" element={<Protected><Layout/></Protected>}>
          <Route index element={<Navigate to="/dashboard" replace/>}/>
          <Route path="dashboard"    element={<Dashboard/>}/>
          <Route path="chat"         element={<Chat/>}/>
          <Route path="chat/:id"     element={<Chat/>}/>
          <Route path="analytics"    element={<Analytics/>}/>
          <Route path="profile"      element={<Profile/>}/>
          <Route path="security2fa"  element={<Security2FA/>}/>
          {/* Admin-only routes */}
          <Route path="models"       element={<AdminOnly><Models/></AdminOnly>}/>
          <Route path="knowledge"    element={<AdminOnly><Knowledge/></AdminOnly>}/>
          <Route path="memory"       element={<AdminOnly><Memory/></AdminOnly>}/>
          <Route path="workflow"     element={<AdminOnly><Workflow/></AdminOnly>}/>
          <Route path="integrations" element={<AdminOnly><Integrations/></AdminOnly>}/>
          <Route path="playground"   element={<AdminOnly><Playground/></AdminOnly>}/>
          <Route path="logs"         element={<AdminOnly><Logs/></AdminOnly>}/>
          <Route path="settings"     element={<AdminOnly><SettingsPage/></AdminOnly>}/>
          <Route path="admin"        element={<AdminOnly><Admin/></AdminOnly>}/>
          <Route path="security"     element={<Navigate to="/security2fa" replace/>}/>
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
