import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'
import { Upload, Trash2, Search, Globe, FileText, File, RefreshCw, Eye } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import clsx from 'clsx'

const DOC_ICON = { pdf: '📕', docx: '📘', txt: '📄', csv: '📊', md: '📝', web: '🌐' }
const STATUS_COLOR = { ready: 'text-success', indexing: 'text-warn', error: 'text-danger' }

export default function Knowledge() {
  const { t } = useTranslation()
  const STATUS_LABEL = { ready: `✓ ${t('status_ready')}`, indexing: `⟳ ${t('status_indexing')}`, error: `✗ ${t('status_error')}` }
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [scrapeUrl, setScrapeUrl] = useState('')
  const [scraping, setScraping] = useState(false)

  const [folders, setFolders] = useState([])
  const [loadingFolders, setLoadingFolders] = useState(false)
  const [selectedFolder, setSelectedFolder] = useState('')
  const [syncingDrive, setSyncingDrive] = useState(false)

  const loadDocs = () => {
    setLoading(true)
    api.listDocs().then(setDocs).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { loadDocs() }, [])

  // Dropzone
  const onDrop = useCallback(async (files) => {
    setUploading(true)
    for (const file of files) {
      try {
        toast.loading(`Mengupload ${file.name}...`, { id: file.name })
        await api.uploadDoc(file)
        toast.success(`${file.name} berhasil diupload!`, { id: file.name })
      } catch (e) {
        toast.error(`${file.name}: ${e.message}`, { id: file.name })
      }
    }
    setUploading(false)
    setTimeout(loadDocs, 1500)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'], 'text/plain': ['.txt'], 'text/csv': ['.csv'], 'text/markdown': ['.md'] },
    multiple: true,
  })

  async function deleteDoc(id, name) {
    if (!confirm(`Hapus "${name}"?`)) return
    try {
      await api.deleteDoc(id)
      toast.success('Dokumen dihapus')
      loadDocs()
    } catch { toast.error('Gagal hapus') }
  }

  async function searchKB() {
    if (!searchQ.trim()) return
    try {
      const r = await api.queryRAG(searchQ)
      setSearchResults(r.results || [])
    } catch { toast.error('Pencarian gagal') }
  }

  async function scrapeWebsite() {
    if (!scrapeUrl.trim()) return
    setScraping(true)
    try {
      const r = await api.scrapeWeb(scrapeUrl)
      toast.success(`Website di-scrape: ${r.chunks || 0} chunks`)
      setScrapeUrl('')
      setTimeout(loadDocs, 1500)
    } catch (e) { toast.error(e.message) }
    finally { setScraping(false) }
  }

  async function loadFolders() {
    setLoadingFolders(true)
    try {
      const r = await api.gdriveFolders()
      setFolders(r.folders || [])
    } catch(e) {
      toast.error('Gagal memuat folder Drive. Pastikan kredensial Service Account terisi.')
    } finally {
      setLoadingFolders(false)
    }
  }

  async function syncGDrive() {
    if (!selectedFolder) return
    setSyncingDrive(true)
    toast.loading('Menyinkronkan dokumen dari Drive...', { id: 'gdrive' })
    try {
      const r = await api.gdriveSync({ folder_id: selectedFolder, collection: 'default' })
      toast.success(r.message, { id: 'gdrive' })
      setTimeout(loadDocs, 2000)
    } catch(e) {
      toast.error(e.message, { id: 'gdrive' })
    } finally {
      setSyncingDrive(false)
      setSelectedFolder('')
      setFolders([]) // Reset to hide the list
    }
  }

  return (
    <div className="p-4 md:p-6 w-full">
      <div className="flex items-center justify-between mb-8">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold text-ink uppercase tracking-tight">{t('kb_title')}</h1>
          <p className="text-sm text-ink-3 font-semibold uppercase tracking-widest opacity-60">{docs.length} {t('indexing_desc')}</p>
        </div>
        <button onClick={loadDocs} className="flex items-center gap-2 px-6 py-3 bg-bg-3 border border-border rounded-xl text-xs font-bold text-ink uppercase tracking-widest hover:bg-bg-4 transition-all shadow-md active:scale-95">
          <RefreshCw size={18} className={clsx(loading && 'animate-spin')} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Doc list */}
        <div className="lg:col-span-2 space-y-4">
          {/* Upload zone */}
          <div {...getRootProps()} className={clsx(
            'border border-dashed rounded-2xl p-10 text-center cursor-pointer transition-all shadow-inner',
            isDragActive ? 'border-accent bg-accent/10' : 'border-border hover:border-accent/40 hover:bg-bg-3'
          )}>
            <input {...getInputProps()} />
            <Upload size={40} className={clsx('mx-auto mb-4 transition-transform', isDragActive ? 'text-accent-2 scale-110' : 'text-ink-3')} />
            <p className="text-lg font-bold text-ink uppercase tracking-tight">
              {uploading ? t('processing') : isDragActive ? t('drop_files_here') : t('upload_rag_desc')}
            </p>
            <p className="text-[10px] text-ink-3 mt-2 font-bold uppercase tracking-widest opacity-50">PDF · DOCX · TXT · CSV · MD — Maks 50MB</p>
          </div>

          {/* Doc list */}
          <div className="space-y-3">
            {loading && <div className="text-sm font-bold text-ink-3 py-6 flex items-center justify-center gap-3 uppercase tracking-widest opacity-60"><RefreshCw size={20} className="animate-spin" /> {t('loading') || 'Loading...'}</div>}
            {!loading && docs.length === 0 && (
              <div className="bg-bg-3 border border-border rounded-2xl p-10 text-center shadow-inner">
                <FileText size={40} className="text-ink-3 mx-auto mb-4 opacity-30" />
                <p className="text-sm font-bold text-ink-3 uppercase tracking-widest opacity-60">{t('no_documents')}</p>
              </div>
            )}
            {docs.map((doc) => (
              <div key={doc.id} className="flex items-center gap-5 p-4 bg-bg-3 border border-border rounded-2xl hover:border-accent/40 transition-all group shadow-sm">
                <div className="text-2xl flex-shrink-0 bg-bg-4 w-12 h-12 rounded-xl flex items-center justify-center shadow-inner border border-border/20">{DOC_ICON[doc.doc_type] || '📄'}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-lg font-bold text-ink truncate tracking-tight uppercase leading-tight">{doc.original_name}</div>
                  <div className="flex items-center gap-3 mt-2 text-[10px] font-bold uppercase tracking-widest">
                    <span className="text-accent-2 bg-accent/10 px-2 py-0.5 rounded border border-accent/20">{doc.doc_type}</span>
                    <span className="text-ink-3 opacity-40">·</span>
                    <span className="text-ink-3">{doc.file_size_kb}KB</span>
                    <span className="text-ink-3 opacity-40">·</span>
                    <span className="text-ink-3">{doc.chunks} chunks</span>
                    <span className="text-ink-3 opacity-40">·</span>
                    <span className={clsx(STATUS_COLOR[doc.status])}>{STATUS_LABEL[doc.status]}</span>
                  </div>
                </div>
                <button
                  onClick={() => deleteDoc(doc.id, doc.original_name)}
                  className="opacity-0 group-hover:opacity-100 p-2.5 rounded-xl hover:bg-danger/10 text-danger transition-all shadow-sm border border-transparent hover:border-danger/30"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Search + Scrape */}
        <div className="space-y-4">
          {/* Search */}
          <div className="bg-bg-3 border border-border rounded-2xl p-5 shadow-lg">
            <h3 className="text-xs font-bold text-ink-3 mb-4 uppercase tracking-widest opacity-60">🔍 Test RAG Search</h3>
            <div className="flex gap-3 mb-4">
              <input
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && searchKB()}
                placeholder="Cari pengetahuan..."
                className="flex-1 bg-bg-2 border border-border rounded-xl px-4 py-3 text-sm font-bold text-ink placeholder-ink-3 outline-none focus:border-accent transition-all shadow-inner"
              />
              <button onClick={searchKB} className="p-3.5 bg-accent hover:bg-accent/80 rounded-xl transition-all shadow-xl shadow-accent/25 active:scale-95">
                <Search size={20} className="text-white" />
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                {searchResults.map((r, i) => (
                  <div key={i} className="p-4 bg-bg-4 rounded-xl border border-border/50 text-[11px] shadow-sm">
                    <div className="font-bold text-accent-2 mb-2 uppercase tracking-tight truncate border-b border-border/40 pb-2">📄 {r.source}</div>
                    <div className="text-ink-2 line-clamp-5 leading-relaxed font-semibold opacity-80">{r.content}</div>
                    <div className="text-[10px] text-ink-3 mt-3 font-bold uppercase tracking-widest flex items-center justify-between">
                       <span>Akurasi:</span>
                       <span className="text-success">{(r.score * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Scrape */}
          <div className="bg-bg-3 border border-border rounded-2xl p-5 shadow-lg">
            <h3 className="text-xs font-bold text-ink-3 mb-4 uppercase tracking-widest opacity-60">🌐 {t('scrape_title')}</h3>
            <input
              value={scrapeUrl}
              onChange={(e) => setScrapeUrl(e.target.value)}
              placeholder="https://example.com/page"
              className="w-full bg-bg-2 border border-border rounded-xl px-4 py-3 text-sm font-bold text-ink placeholder-ink-3 outline-none focus:border-accent mb-4 transition-all shadow-inner"
            />
            <button
              onClick={scrapeWebsite}
              disabled={scraping || !scrapeUrl.trim()}
              className="w-full flex items-center justify-center gap-3 py-4 bg-bg-4 hover:bg-info/10 border border-info/30 text-info rounded-xl text-xs font-bold uppercase tracking-widest disabled:opacity-40 transition-all shadow-md active:scale-95"
            >
              <Globe size={18} className={clsx(scraping && 'animate-spin')} /> {scraping ? 'Scraping...' : 'Scrape & Index'}
            </button>
          </div>

          {/* GDrive Import */}
          <div className="bg-bg-3 border border-border rounded-2xl p-5 shadow-lg">
            <h3 className="text-xs font-bold text-ink-3 mb-4 uppercase tracking-widest opacity-60">☁️ {t('gdrive_title')}</h3>
            
            {folders.length === 0 && !loadingFolders ? (
              <button
                onClick={loadFolders}
                className="w-full flex items-center justify-center gap-3 py-4 bg-bg-4 hover:bg-success/10 border border-success/30 text-success rounded-xl text-xs font-bold uppercase tracking-widest transition-all shadow-md active:scale-95"
              >
                <File size={18} /> Pilih Folder Drive
              </button>
            ) : null}

            {loadingFolders && (
              <div className="flex items-center gap-3 text-xs font-bold text-ink-3 py-4 justify-center uppercase tracking-widest opacity-60">
                <RefreshCw size={18} className="animate-spin" /> Memuat folder...
              </div>
            )}

            {folders.length > 0 && (
              <div className="space-y-4 mt-2 animate-fade">
                <select
                  value={selectedFolder}
                  onChange={(e) => setSelectedFolder(e.target.value)}
                  className="w-full bg-bg-2 border border-border rounded-xl px-4 py-3 text-sm font-bold text-ink outline-none focus:border-accent transition-all shadow-inner"
                >
                  <option value="">-- Pilih Folder --</option>
                  {folders.map(f => (
                    <option key={f.id} value={f.id}>📁 {f.name}</option>
                  ))}
                </select>
                <div className="flex gap-3">
                  <button onClick={() => setFolders([])} className="flex-1 py-3 bg-bg-4 border border-border rounded-xl text-[10px] font-bold text-ink-3 uppercase tracking-widest transition-all hover:bg-bg-5 active:scale-95">Batal</button>
                  <button
                    onClick={syncGDrive}
                    disabled={syncingDrive || !selectedFolder}
                    className="flex-[2] flex items-center justify-center gap-3 py-3 bg-bg-4 hover:bg-success/10 border border-success/30 text-success rounded-xl text-[10px] font-bold uppercase tracking-widest disabled:opacity-40 transition-all shadow-md active:scale-95"
                  >
                    {syncingDrive ? 'Sinkronisasi...' : 'Sync ke RAG'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Tips */}
          <div className="bg-bg-3 border border-border rounded-2xl p-5 shadow-inner">
            <h3 className="text-xs font-bold text-ink mb-4 uppercase tracking-widest opacity-60">💡 {t('rag_tips_title')}</h3>
            <ul className="text-xs text-ink-3 space-y-3 font-semibold leading-relaxed opacity-80 uppercase tracking-tight">
              <li className="flex gap-2"><span className="text-accent-2">•</span> <span>Upload PDF laporan → AI bisa menjawab dari laporan</span></li>
              <li className="flex gap-2"><span className="text-accent-2">•</span> <span>Scrape website → AI tahu tentang produk kamu</span></li>
              <li className="flex gap-2"><span className="text-accent-2">•</span> <span>Aktifkan RAG di chat agar AI gunakan basis data</span></li>
              <li className="flex gap-2"><span className="text-accent-2">•</span> <span>Makin banyak data = AI makin akurat & relevan</span></li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
