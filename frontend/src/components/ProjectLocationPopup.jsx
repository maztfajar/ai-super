import { useState, useEffect } from 'react'
import { X, FolderOpen } from 'lucide-react'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'

export default function ProjectLocationPopup({ isOpen, onClose, sessionId, onLocationSet }) {
  const [projectPath, setProjectPath] = useState('')
  const [isLoading, setIsLoading] = useState(false)

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

  const handleBrowse = () => {
    // Create a simple file input for directory selection
    const input = document.createElement('input')
    input.type = 'file'
    input.webkitdirectory = true
    input.multiple = false
    
    input.onchange = (e) => {
      if (e.target.files.length > 0) {
        // Get the directory path from the first file
        const fullPath = e.target.files[0].webkitRelativePath
        const directoryPath = fullPath.split('/')[0]
        setProjectPath(directoryPath)
      }
    }
    
    input.click()
  }

  const getDefaultPath = () => {
    return '/home/' + (typeof window !== 'undefined' && window.electronAPI ? 
      window.electronAPI.getUsername() : 
      (localStorage.getItem('username') || 'user'))
  }

  if (!isOpen) return null

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
                onClick={handleBrowse}
                className="px-3 py-2 bg-bg-4 hover:bg-bg-5 border border-border rounded-lg text-ink-2 transition-colors"
                title="Pilih folder"
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
              onClick={() => setProjectPath('/home/ppidpengasih/Desktop')}
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
