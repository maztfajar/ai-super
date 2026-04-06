import React, { useState, useEffect } from 'react'
import { Folder, FolderPlus, ArrowLeft, Check, Loader2, X, ChevronRight } from 'lucide-react'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'
import clsx from 'clsx'

export default function DriveFolderPicker({ onClose, onConfirm }) {
  const [folders, setFolders] = useState([])
  const [loading, setLoading] = useState(true)
  const [navStack, setNavStack] = useState([{ id: null, name: 'Google Drive Root' }])
  const [showCreate, setShowCreate] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [creating, setCreating] = useState(false)
  const [format, setFormat] = useState('pdf')

  useEffect(() => {
    loadFolders()
  }, [])

  async function loadFolders() {
    setLoading(true)
    try {
      const res = await api.getDriveFolders()
      if (res.status === 'success') {
        setFolders(res.folders || [])
      }
    } catch (e) {
      toast.error(e.message || 'Gagal memuat folder Google Drive')
    } finally {
      setLoading(false)
    }
  }

  const currentLevelId = navStack[navStack.length - 1].id

  // Hanya tampilkan folder yang parent-nya cocok dengan currentLevelId
  // Drive API mengembalikan parents berupa array. Jika root, parents-nya tidak ada, tapi kadang ada yg menganggap root itu ID tertentu.
  // Untuk menyederhanakan (karena list_drive_folders tidak return exact hierarchy sometimes), 
  // kita anggap root jika tidak ada parents atau jika folder adalah bagian dari root.
  const visibleFolders = folders.filter((f) => {
    if (currentLevelId === null) {
      // Root: tidak punya parents
      return !f.parents || f.parents.length === 0
    } else {
      return f.parents && f.parents.includes(currentLevelId)
    }
  })

  // Tapi ada kelemahan: Jika folder dishare ke root padahal ada parent, dll.
  // Jika di root tidak ada yg matching, kita munculkan semua yg tidak ada parentnya
  const displayedFolders = currentLevelId === null && visibleFolders.length === 0 
      ? folders.filter(f => !f.parents) // fallback if visible is empty
      : visibleFolders

  // Agar user tidak stuck jika Drive root behaviour unik
  const actualDisplayed = displayedFolders.length > 0 ? displayedFolders : 
        (currentLevelId === null ? folders : []) // Tampilkan semua di root jk filter gagal

  const handleCreateFolder = async (e) => {
    e.preventDefault()
    if (!newFolderName.trim()) return
    setCreating(true)
    try {
      const res = await api.createDriveFolder({
        folder_name: newFolderName,
        parent_id: currentLevelId
      })
      toast.success('Folder dibuat')
      setNewFolderName('')
      setShowCreate(false)
      loadFolders() // reload
    } catch(e) {
      toast.error('Gagal membuat folder')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 animate-fade">
      <div className="w-full max-w-md bg-bg-2 border border-border-2 animate-fade-in-up flex flex-col overflow-hidden rounded-2xl shadow-2xl">
        {/* Header */}
        <div className="p-4 border-b border-border bg-bg flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink flex items-center gap-2">
            <Folder className="text-accent" size={16} /> Pilih Folder Drive
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-bg-3 rounded-full text-ink-3 hover:text-ink transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Navigation Breadcrumbs */}
        <div className="px-4 py-2 border-b border-border-2 bg-bg-3 flex items-center gap-1 overflow-x-auto whitespace-nowrap text-xs text-ink-2 no-scrollbar">
          {navStack.map((nav, idx) => (
            <React.Fragment key={idx}>
              {idx > 0 && <ChevronRight size={12} className="text-ink-3 flex-shrink-0" />}
              <button
                disabled={idx === navStack.length - 1}
                onClick={() => setNavStack(navStack.slice(0, idx + 1))}
                className={clsx(
                  "hover:text-accent transition-colors truncate max-w-[120px]",
                  idx === navStack.length - 1 && "font-semibold text-ink cursor-default pointer-events-none"
                )}
              >
                {nav.name}
              </button>
            </React.Fragment>
          ))}
        </div>

        {/* Content */}
        <div className="p-2 flex-1 overflow-y-auto max-h-[40vh] min-h-[40vh]">
          {loading ? (
            <div className="h-full flex items-center justify-center text-ink-3 text-sm gap-2">
              <Loader2 size={16} className="animate-spin" /> Memuat...
            </div>
          ) : (
             <div className="space-y-1">
               {currentLevelId !== null && (
                 <button
                   onClick={() => setNavStack(navStack.slice(0, -1))}
                   className="w-full flex items-center gap-3 p-2.5 hover:bg-bg-3 rounded-lg text-sm text-ink transition-colors"
                 >
                   <ArrowLeft size={16} className="text-ink-3" />
                   <span className="font-medium text-ink-2">.. (Kembali)</span>
                 </button>
               )}
               
               {actualDisplayed.map((f) => (
                 <button
                   key={f.id}
                   onClick={() => setNavStack([...navStack, { id: f.id, name: f.name }])}
                   className="w-full flex items-center gap-3 p-2.5 hover:bg-accent/10 hover:text-accent rounded-lg text-sm text-ink transition-all group"
                 >
                   <Folder size={16} className="text-accent group-hover:text-accent-2" fill="currentColor" fillOpacity={0.2} />
                   <span className="truncate">{f.name}</span>
                 </button>
               ))}
               
               {actualDisplayed.length === 0 && currentLevelId !== null && (
                 <div className="py-8 text-center text-xs text-ink-3">
                   Folder ini kosong
                 </div>
               )}
             </div>
          )}
        </div>

        {/* Create Folder Section */}
        {showCreate ? (
          <form onSubmit={handleCreateFolder} className="p-3 border-t border-border-2 bg-bg-3 animate-fade">
            <div className="flex items-center gap-2">
              <input 
                autoFocus
                type="text" 
                value={newFolderName}
                onChange={e => setNewFolderName(e.target.value)}
                placeholder="Nama folder baru..."
                className="flex-1 text-sm bg-bg border border-border-2 rounded-lg px-3 py-1.5 focus:border-accent text-ink outline-none"
                disabled={creating}
              />
              <button disabled={creating || !newFolderName.trim()} type="submit" className="p-1.5 bg-accent hover:bg-accent/80 text-white rounded-lg disabled:opacity-50">
                {creating ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
              </button>
              <button disabled={creating} type="button" onClick={() => setShowCreate(false)} className="p-1.5 hover:bg-danger/20 text-danger rounded-lg">
                <X size={16} />
              </button>
            </div>
          </form>
        ) : null}

        {!showCreate && (
           <div className="border-t border-border-2 bg-bg-3">
             {/* Format Selection */}
             <div className="px-4 py-2 border-b border-border border-opacity-50 flex items-center justify-between text-xs text-ink-2">
                 <span>Format Simpan:</span>
                 <select 
                    value={format}
                    onChange={(e) => setFormat(e.target.value)}
                    className="bg-bg border border-border-2 rounded-md px-2 py-1 outline-none text-ink cursor-pointer hover:border-accent focus:border-accent"
                 >
                    <option value="pdf">PDF Document</option>
                    <option value="docx">Word (.docx)</option>
                    <option value="xlsx">Excel (.xlsx)</option>
                    <option value="csv">CSV Data</option>
                    <option value="txt">Plain Text</option>
                    <option value="md">Markdown</option>
                 </select>
             </div>
             {/* Footer Actions */}
             <div className="p-3 flex justify-between items-center">
                <button 
                  onClick={() => setShowCreate(true)}
                  className="flex items-center gap-1.5 text-xs text-accent hover:text-accent-2 transition-colors font-medium px-2 py-1"
                >
                  <FolderPlus size={14} /> Buat Folder
                </button>
                <button 
                  onClick={() => onConfirm(navStack[navStack.length - 1], format)}
                  className="flex items-center gap-1.5 px-4 py-2 bg-accent hover:bg-accent/80 shadow text-white font-medium text-xs rounded-lg transition-all"
                >
                  <Check size={14} /> Simpan
                </button>
             </div>
          </div>
        )}
      </div>
    </div>
  )
}
