import { useState, useEffect, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'
import { Upload, Trash2, Search, Globe, FileText, File, RefreshCw, Eye } from 'lucide-react'
import clsx from 'clsx'

const DOC_ICON = { pdf: '📕', docx: '📘', txt: '📄', csv: '📊', md: '📝', web: '🌐' }
const STATUS_COLOR = { ready: 'text-success', indexing: 'text-warn', error: 'text-danger' }
const STATUS_LABEL = { ready: '✓ Siap', indexing: '⟳ Indexing...', error: '✗ Error' }

export default function Knowledge() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [scrapeUrl, setScrapeUrl] = useState('')
  const [scraping, setScraping] = useState(false)

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

  return (
    <div className="p-4 md:p-6 w-full">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-ink">Knowledge Base (RAG)</h1>
          <p className="text-xs text-ink-3 mt-0.5">{docs.length} dokumen · ChromaDB vector store</p>
        </div>
        <button onClick={loadDocs} className="flex items-center gap-1.5 px-3 py-1.5 border border-border-2 rounded-lg text-xs text-ink-2 hover:bg-bg-4 transition-colors">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Doc list */}
        <div className="lg:col-span-2 space-y-3">
          {/* Upload zone */}
          <div {...getRootProps()} className={clsx(
            'border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all',
            isDragActive ? 'border-accent bg-accent/5' : 'border-border hover:border-border-2 hover:bg-bg-3'
          )}>
            <input {...getInputProps()} />
            <Upload size={24} className={clsx('mx-auto mb-2', isDragActive ? 'text-accent-2' : 'text-ink-3')} />
            <p className="text-sm font-medium text-ink-2">
              {uploading ? 'Mengupload...' : isDragActive ? 'Lepas file di sini!' : 'Drag & drop atau klik untuk upload'}
            </p>
            <p className="text-xs text-ink-3 mt-1">PDF · DOCX · TXT · CSV · MD — Maks {50}MB</p>
          </div>

          {/* Doc list */}
          <div className="space-y-2">
            {loading && <div className="text-xs text-ink-3 py-4 flex items-center gap-2"><RefreshCw size={12} className="animate-spin" /> Memuat dokumen...</div>}
            {!loading && docs.length === 0 && (
              <div className="bg-bg-3 border border-border rounded-xl p-6 text-center">
                <FileText size={28} className="text-ink-3 mx-auto mb-2" />
                <p className="text-sm text-ink-3">Belum ada dokumen. Upload untuk mulai!</p>
              </div>
            )}
            {docs.map((doc) => (
              <div key={doc.id} className="flex items-center gap-3 p-3 bg-bg-3 border border-border rounded-xl hover:border-border-2 transition-colors group">
                <div className="text-xl flex-shrink-0">{DOC_ICON[doc.doc_type] || '📄'}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-ink truncate">{doc.original_name}</div>
                  <div className="flex items-center gap-2 mt-0.5 text-[10px]">
                    <span className="text-ink-3">{doc.doc_type.toUpperCase()}</span>
                    <span className="text-ink-3">·</span>
                    <span className="text-ink-3">{doc.file_size_kb}KB</span>
                    <span className="text-ink-3">·</span>
                    <span className="text-ink-3">{doc.chunks} chunks</span>
                    <span className="text-ink-3">·</span>
                    <span className={STATUS_COLOR[doc.status]}>{STATUS_LABEL[doc.status]}</span>
                  </div>
                </div>
                <button
                  onClick={() => deleteDoc(doc.id, doc.original_name)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-danger/10 transition-all"
                >
                  <Trash2 size={13} className="text-danger" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Search + Scrape */}
        <div className="space-y-3">
          {/* Search */}
          <div className="bg-bg-3 border border-border rounded-xl p-3">
            <h3 className="text-xs font-semibold text-ink mb-2">🔍 Test RAG Search</h3>
            <div className="flex gap-2 mb-3">
              <input
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && searchKB()}
                placeholder="Cari di knowledge base..."
                className="flex-1 bg-bg-4 border border-border-2 rounded-lg px-2.5 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent"
              />
              <button onClick={searchKB} className="px-3 py-2 bg-accent hover:bg-accent/80 rounded-lg">
                <Search size={13} className="text-white" />
              </button>
            </div>
            {searchResults.length > 0 && (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {searchResults.map((r, i) => (
                  <div key={i} className="p-2 bg-bg-4 rounded-lg border border-border text-[10px]">
                    <div className="font-medium text-accent-2 mb-1 truncate">📄 {r.source}</div>
                    <div className="text-ink-3 line-clamp-3">{r.content}</div>
                    <div className="text-ink-3 mt-1">Score: {(r.score * 100).toFixed(0)}%</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Scrape */}
          <div className="bg-bg-3 border border-border rounded-xl p-3">
            <h3 className="text-xs font-semibold text-ink mb-2">🌐 Scrape Website</h3>
            <input
              value={scrapeUrl}
              onChange={(e) => setScrapeUrl(e.target.value)}
              placeholder="https://example.com/page"
              className="w-full bg-bg-4 border border-border-2 rounded-lg px-2.5 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent mb-2"
            />
            <button
              onClick={scrapeWebsite}
              disabled={scraping || !scrapeUrl.trim()}
              className="w-full flex items-center justify-center gap-1.5 py-2 bg-info/10 hover:bg-info/20 border border-info/20 text-info rounded-lg text-xs font-medium disabled:opacity-50 transition-colors"
            >
              <Globe size={12} /> {scraping ? 'Scraping...' : 'Scrape & Index'}
            </button>
          </div>

          {/* Tips */}
          <div className="bg-bg-3 border border-border rounded-xl p-3">
            <h3 className="text-xs font-semibold text-ink mb-2">💡 Tips RAG</h3>
            <ul className="text-[10px] text-ink-3 space-y-1.5">
              <li>• Upload PDF laporan → AI bisa menjawab dari laporan</li>
              <li>• Scrape website perusahaan → AI tahu tentang produk kamu</li>
              <li>• Aktifkan tombol 📚 RAG di chat agar AI gunakan knowledge base</li>
              <li>• Makin banyak dokumen = AI makin relevan</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
