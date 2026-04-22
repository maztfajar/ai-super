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
        <div className="bg-bg-2 border border-border rounded-xl p-6 w-full max-w-md mx-4 flex flex-col h-[500px]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-ink">Pilih Folder Server</h3>
            <button onClick={() => setShowBrowser(false)} className="p-2 rounded-lg hover:bg-bg-4 text-ink-2 transition-colors">
              <X size={20} />
            </button>
          </div>
          
          <div className="mb-2 text-sm font-mono text-ink-2 bg-bg-3 p-2 rounded truncate border border-border">
            {browserPath}
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-1 mb-4 border border-border rounded-lg bg-bg-3 p-2">
            {browserLoading ? (
              <div className="text-center py-8 text-ink-3">Memuat folder...</div>
            ) : (
              <>
                <div 
                  className="p-2 hover:bg-bg-4 cursor-pointer rounded flex items-center gap-3 text-ink transition-colors"
                  onClick={() => {
                    const parentPath = browserPath.split('/').slice(0, -1).join('/') || '/'
                    handleBrowse(parentPath)
                  }}
                >
                  <FolderOpen size={16} className="text-accent shrink-0" /> 
                  <span className="truncate">.. (Kembali)</span>
                </div>
                {directories.length === 0 && (
                  <div className="text-center py-4 text-ink-3 text-sm">Folder kosong</div>
                )}
                {directories.map(dir => (
                  <div 
                    key={dir.path}
                    className="p-2 hover:bg-bg-4 cursor-pointer rounded flex items-center gap-3 text-ink transition-colors"
                    onClick={() => handleBrowse(dir.path)}
                  >
                    <FolderOpen size={16} className="text-accent shrink-0" /> 
                    <span className="truncate">{dir.name}</span>
                  </div>
                ))}
              </>
            )}
          </div>
          
          <div className="flex gap-3 mt-auto pt-2">
            <button 
              onClick={() => setShowBrowser(false)} 
              className="flex-1 px-4 py-2 border border-border rounded-lg text-ink-2 hover:bg-bg-4 transition-colors"
            >
              Batal
            </button>
            <button 
              onClick={() => { 
                setProjectPath(browserPath); 
                setShowBrowser(false);
              }} 
              className="flex-1 px-4 py-2 bg-accent hover:bg-accent/80 text-white rounded-lg transition-colors"
            >
              Pilih Folder Ini
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-bg-2 border border-border rounded-xl p-6 w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-ink">
            📁 Lokasi Penyimpanan Proyek
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-bg-4 text-ink-2 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink mb-2">
              Pilih lokasi untuk menyimpan file proyek:
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={projectPath}
                onChange={(e) => setProjectPath(e.target.value)}
                placeholder={getDefaultPath()}
                className="flex-1 px-3 py-2 border border-border rounded-lg bg-bg-3 text-ink placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent"
              />
              <button
                onClick={() => handleBrowse('')}
                className="px-3 py-2 bg-bg-4 hover:bg-bg-5 border border-border rounded-lg text-ink-2 transition-colors"
                title="Pilih folder dari server"
              >
                <FolderOpen size={18} />
              </button>
            </div>
            <p className="text-xs text-ink-3 mt-1">
              💡 Proyek akan disimpan di folder ini. AI akan menggunakan lokasi ini untuk semua file yang dibuat.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex gap-2">
            <button
              onClick={() => setProjectPath(getDefaultPath())}
              className="flex-1 px-3 py-2 bg-bg-4 hover:bg-bg-5 border border-border rounded-lg text-ink-2 transition-colors text-sm"
            >
              🏠 Folder Home
            </button>
            <button
              onClick={() => setProjectPath(getDefaultPath() + '/Desktop')}
              className="flex-1 px-3 py-2 bg-bg-4 hover:bg-bg-5 border border-border rounded-lg text-ink-2 transition-colors text-sm"
            >
              🖥️ Desktop
            </button>
            <button
              onClick={() => setProjectPath('/tmp')}
              className="flex-1 px-3 py-2 bg-bg-4 hover:bg-bg-5 border border-border rounded-lg text-ink-2 transition-colors text-sm"
            >
              📂 Temp
            </button>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-border rounded-lg text-ink-2 hover:bg-bg-4 transition-colors"
          >
            Batal
          </button>
          <button
            onClick={handleSave}
            disabled={isLoading || !projectPath.trim()}
            className="flex-1 px-4 py-2 bg-accent hover:bg-accent/80 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Menyimpan...' : 'Simpan Lokasi'}
          </button>
        </div>
      </div>
    </div>
  )
}
