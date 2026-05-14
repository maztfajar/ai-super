import { useState, useEffect } from 'react'
import { X, FolderOpen } from 'lucide-react'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'

export default function ProjectLocationPopup({ isOpen, onClose, sessionId, onLocationSet }) {
  const [projectPath, setProjectPath] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showBrowser, setShowBrowser] = useState(false)
  const [browserPath, setBrowserPath] = useState('')
  const [directories, setDirectories] = useState([])
  const [browserLoading, setBrowserLoading] = useState(false)

  useEffect(() => {
    // Load existing project location when popup opens
    if (isOpen && sessionId) {
      loadProjectLocation()
    }
  }, [isOpen, sessionId])

  const loadProjectLocation = async () => {
    try {
      const response = await api.get(`/chat/get_project_location/${sessionId}`)
      if (response.project_path) {
        setProjectPath(response.project_path)
      }
    } catch (error) {
      console.error('Failed to load project location:', error)
    }
  }

  const handleSave = async () => {
    if (!projectPath.trim()) {
      toast.error('Silakan masukkan lokasi proyek')
      return
    }

    setIsLoading(true)
    try {
      await api.post('/chat/set_project_location', {
        session_id: sessionId,
        project_path: projectPath.trim()
      })
      
      toast.success('Lokasi proyek berhasil disimpan')
      onLocationSet && onLocationSet(projectPath.trim())
      onClose()
    } catch (error) {
      console.error('Failed to save project location:', error)
      toast.error(error.detail || 'Gagal menyimpan lokasi proyek')
    } finally {
      setIsLoading(false)
    }
  }

  const handleBrowse = async (path = '') => {
    setBrowserLoading(true)
    setShowBrowser(true)
    try {
      // Determine the path to browse, default to current projectPath or home
      const targetPath = path || projectPath || getDefaultPath()
      const response = await api.post('/chat/list_directories', { path: targetPath })
      setBrowserPath(response.path)
      setDirectories(response.directories)
    } catch (error) {
      console.error('Failed to load directories:', error)
      toast.error('Gagal memuat daftar folder server')
    } finally {
      setBrowserLoading(false)
    }
  }

  const getDefaultPath = () => {
    return '/home/' + (typeof window !== 'undefined' && window.electronAPI ? 
      window.electronAPI.getUsername() : 
      (localStorage.getItem('username') || 'user'))
  }

  if (!isOpen) return null

  if (showBrowser) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-bg-2 border border-border rounded-xl p-8 w-full max-w-lg mx-4 flex flex-col h-[600px]">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-xl font-semibold text-ink tracking-tight uppercase">Pilih Folder Server</h3>
            <button onClick={() => setShowBrowser(false)} className="p-2 rounded-lg hover:bg-bg-4 text-ink-2 transition-colors">
              <X size={20} />
            </button>
          </div>
          
          <div className="mb-3 text-sm font-mono text-ink-2 bg-bg-3 px-4 py-3 rounded-lg truncate border border-border font-semibold">
            {browserPath}
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-1 mb-4 border border-border rounded-lg bg-bg-3 p-2">
            {browserLoading ? (
              <div className="text-center py-8 text-ink-3">Memuat folder...</div>
            ) : (
              <>
                  <div 
                    className="p-3 hover:bg-bg-4 cursor-pointer rounded-lg flex items-center gap-4 text-sm font-semibold text-ink transition-all"
                    onClick={() => {
                      const parentPath = browserPath.split('/').slice(0, -1).join('/') || '/'
                      handleBrowse(parentPath)
                    }}
                  >
                    <FolderOpen size={18} className="text-accent shrink-0" /> 
                    <span className="truncate">.. (Kembali)</span>
                  </div>
                  {directories.length === 0 && (
                    <div className="text-center py-8 text-ink-3 text-base font-medium italic">Folder kosong</div>
                  )}
                  {directories.map(dir => (
                    <div 
                      key={dir.path}
                      className="p-3 hover:bg-bg-4 cursor-pointer rounded-lg flex items-center gap-4 text-sm font-semibold text-ink transition-all"
                      onClick={() => handleBrowse(dir.path)}
                    >
                      <FolderOpen size={18} className="text-accent shrink-0" /> 
                      <span className="truncate">{dir.name}</span>
                    </div>
                  ))}
              </>
            )}
          </div>
          
          <div className="flex gap-4 mt-auto pt-4">
            <button 
              onClick={() => setShowBrowser(false)} 
              className="flex-1 px-6 py-3 border border-border rounded-xl text-sm font-semibold text-ink-2 hover:bg-bg-4 transition-all"
            >
              Batal
            </button>
            <button 
              onClick={() => { 
                setProjectPath(browserPath); 
                setShowBrowser(false);
              }} 
              className="flex-[1.5] px-6 py-3 bg-accent hover:bg-accent/85 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-accent/20"
            >
              Pilih Folder Ini
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-bg-2 border border-border rounded-2xl p-8 w-full max-w-lg mx-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold text-ink uppercase tracking-tight">
            📁 Lokasi Proyek
          </h3>
          <button
            onClick={onClose}
            className="p-2.5 rounded-xl hover:bg-bg-4 text-ink-3 hover:text-ink transition-all"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-6">
          <div>
            <label className="block text-base font-semibold text-ink mb-2.5">
              Pilih lokasi untuk menyimpan file proyek:
            </label>
            <div className="flex gap-3">
              <input
                type="text"
                value={projectPath}
                onChange={(e) => setProjectPath(e.target.value)}
                placeholder={getDefaultPath()}
                className="flex-1 px-4 py-3 border border-border rounded-xl bg-bg-3 text-sm text-ink font-mono placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent transition-all"
              />
              <button
                onClick={() => handleBrowse('')}
                className="px-4 py-3 bg-bg-4 hover:bg-bg-5 border border-border rounded-xl text-ink-2 transition-all shadow-sm"
                title="Pilih folder dari server"
              >
                <FolderOpen size={20} />
              </button>
            </div>
            <p className="text-xs text-ink-3 mt-2 font-medium leading-relaxed">
              💡 Proyek akan disimpan di folder ini. AI akan menggunakan lokasi ini untuk semua file yang dibuat.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex gap-3">
            <button
              onClick={() => setProjectPath(getDefaultPath())}
              className="flex-1 px-3 py-2.5 bg-bg-4 hover:bg-bg-5 border border-border rounded-xl text-ink-2 transition-all text-xs font-bold uppercase tracking-tight"
            >
              🏠 Home
            </button>
            <button
              onClick={() => setProjectPath(getDefaultPath() + '/Desktop')}
              className="flex-1 px-3 py-2.5 bg-bg-4 hover:bg-bg-5 border border-border rounded-xl text-ink-2 transition-all text-xs font-bold uppercase tracking-tight"
            >
              🖥️ Desktop
            </button>
            <button
              onClick={() => setProjectPath('/tmp')}
              className="flex-1 px-3 py-2.5 bg-bg-4 hover:bg-bg-5 border border-border rounded-xl text-ink-2 transition-all text-xs font-bold uppercase tracking-tight"
            >
              📂 Temp
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4 mt-8">
          <button
            onClick={onClose}
            className="flex-1 px-6 py-3 border border-border rounded-xl text-sm font-semibold text-ink-2 hover:bg-bg-4 transition-all"
          >
            Batal
          </button>
          <button
            onClick={handleSave}
            disabled={isLoading || !projectPath.trim()}
            className="flex-[1.5] px-6 py-3 bg-accent hover:bg-accent/85 text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-accent/25 disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
          >
            {isLoading ? 'Menyimpan...' : 'Simpan Lokasi'}
          </button>
        </div>
      </div>
    </div>
  )
}
