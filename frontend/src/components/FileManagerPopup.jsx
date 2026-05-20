// components/FileManagerPopup.jsx
// Pop up File Manager yang muncul saat user minta build app atau edit file

import { useState, useEffect, useCallback, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

const ICON = {
  folder:  "📁",
  file:    "📄",
  js:      "🟨",
  jsx:     "⚛️",
  ts:      "🔷",
  tsx:     "⚛️",
  py:      "🐍",
  css:     "🎨",
  html:    "🌐",
  json:    "📋",
  md:      "📝",
  txt:     "📃",
  png:     "🖼️",
  jpg:     "🖼️",
  svg:     "🎭",
  env:     "🔑",
  sh:      "⚙️",
};

function getIcon(item) {
  if (item.type === "folder") return ICON.folder;
  return ICON[item.extension] || ICON.file;
}

function formatSize(bytes) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// ─────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────

/**
 * @param {Object} props
 * @param {boolean} props.isOpen
 * @param {"browse"|"save_new"} props.mode
 * @param {string} props.intent - "FILE_SYSTEM" | "BUILD_APP"
 * @param {string} props.pendingMessage - pesan user yang di-hold
 * @param {function} props.onConfirm(selectedPath: string) - user klik confirm
 * @param {function} props.onClose
 */
export default function FileManagerPopup({ isOpen, mode, intent, pendingMessage, onConfirm, onClose }) {
  const [currentPath, setCurrentPath] = useState("");
  const [items, setItems] = useState([]);
  const [breadcrumbs, setBreadcrumbs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);

  // save_new mode
  const [newProjectName, setNewProjectName] = useState("");
  const [nameError, setNameError] = useState("");

  // create folder mode
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [folderError, setFolderError] = useState("");

  const inputRef = useRef(null);
  const overlayRef = useRef(null);

  // ── Load directory ──────────────────────────
  const loadDirectory = useCallback(async (path = "") => {
    setLoading(true);
    setError(null);
    setSelectedItem(null);

    try {
      const res = await fetch(`${API_BASE}/file-manager/browse?path=${encodeURIComponent(path)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      setCurrentPath(data.current_path);
      setBreadcrumbs(data.breadcrumbs);

      // filter: browse mode tampilkan semua, save_new hanya folder
      const filtered = mode === "save_new"
        ? data.items.filter(i => i.type === "folder")
        : data.items;

      setItems(filtered);
    } catch (err) {
      setError("Gagal memuat direktori. Pastikan backend berjalan.");
    } finally {
      setLoading(false);
    }
  }, [mode]);

  // ── Reset & load saat popup dibuka ──────────
  useEffect(() => {
    if (isOpen) {
      loadDirectory("");
      setSelectedItem(null);
      setNewProjectName("");
      setNewFolderName("");
      setNameError("");
      setFolderError("");
      setShowNewFolder(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, loadDirectory]);

  // ── Keyboard: Escape tutup popup ────────────
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape" && isOpen) onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  // ── Create folder ────────────────────────────
  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) {
      setFolderError("Nama folder tidak boleh kosong");
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/file-manager/create-folder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ parent_path: currentPath, folder_name: newFolderName.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        setFolderError(data.detail || "Gagal membuat folder");
        return;
      }
      setShowNewFolder(false);
      setNewFolderName("");
      setFolderError("");
      loadDirectory(currentPath);
    } catch {
      setFolderError("Error membuat folder");
    }
  };

  // ── Confirm selection ─────────────────────────
  const handleConfirm = async () => {
    if (mode === "save_new") {
      if (!newProjectName.trim()) {
        setNameError("Nama project tidak boleh kosong");
        return;
      }
      const dir = selectedItem?.type === "folder" ? selectedItem.path : currentPath;
      const path = dir ? `${dir}/${newProjectName.trim()}` : newProjectName.trim();
      onConfirm(path);
    } else {
      // browse mode — harus ada file/folder yang dipilih
      if (!selectedItem) {
        setError("Pilih file atau folder terlebih dahulu");
        return;
      }
      onConfirm(selectedItem.path);
    }
  };

  const confirmLabel = mode === "save_new" ? "Simpan di Sini" : "Pilih";
  const title = mode === "save_new"
    ? "📦 Pilih Lokasi Project"
    : "📂 Pilih File / Folder";

  const subtext = mode === "save_new"
    ? "Pilih folder tempat project baru akan disimpan"
    : "Navigasi dan pilih file atau folder yang ingin diedit";

  if (!isOpen) return null;

  return (
    <div
      ref={overlayRef}
      onClick={(e) => { if (e.target === overlayRef.current) onClose(); }}
      style={{
        position: "fixed", inset: 0, zIndex: 9999,
        background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)",
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: "16px",
        animation: "fm-fade-in 0.15s ease",
      }}
    >
      <style>{`
        @keyframes fm-fade-in { from { opacity: 0; } to { opacity: 1; } }
        @keyframes fm-slide-up { from { transform: translateY(12px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .fm-item:hover { background: rgba(128,128,128,0.08); }
        .fm-item.selected { background: rgba(59,130,246,0.12); outline: 1px solid rgba(59,130,246,0.35); border-radius: 6px; }
        .fm-item.folder { cursor: pointer; }
        .fm-btn { cursor: pointer; border: none; border-radius: 8px; font-size: 13px; padding: 8px 16px; font-weight: 500; transition: opacity .15s, transform .1s; }
        .fm-btn:hover { opacity: 0.85; }
        .fm-btn:active { transform: scale(0.97); }
        .fm-btn-primary { background: #2563eb; color: #fff; }
        .fm-btn-ghost { background: transparent; color: #6b7280; border: 1px solid #e5e7eb; }
        .fm-btn-sm { padding: 5px 12px; font-size: 12px; }
        .fm-input { width: 100%; box-sizing: border-box; padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 8px; font-size: 13px; outline: none; transition: border-color .15s; background: #fff; color: #111; }
        .fm-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
        @media (prefers-color-scheme: dark) {
          .fm-input { background: #1f2937; color: #f9fafb; border-color: #374151; }
          .fm-btn-ghost { color: #9ca3af; border-color: #374151; }
        }
        .fm-crumb { background: none; border: none; cursor: pointer; color: #6b7280; font-size: 12px; padding: 2px 6px; border-radius: 4px; transition: background .1s; }
        .fm-crumb:hover { background: rgba(128,128,128,0.1); color: #111; }
        .fm-crumb.active { color: #111; font-weight: 500; cursor: default; }
        @media (prefers-color-scheme: dark) {
          .fm-crumb:hover { color: #f9fafb; }
          .fm-crumb.active { color: #f9fafb; }
        }
      `}</style>

      <div style={{
        background: "var(--color-background-primary, #fff)",
        borderRadius: 16,
        boxShadow: "0 20px 60px rgba(0,0,0,0.2)",
        width: "100%", maxWidth: 560,
        maxHeight: "80vh",
        display: "flex", flexDirection: "column",
        overflow: "hidden",
        animation: "fm-slide-up 0.2s ease",
      }}>

        {/* Header */}
        <div style={{ padding: "18px 20px 14px", borderBottom: "1px solid rgba(128,128,128,0.12)" }}>
          <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
            <div>
              <p style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--color-text-primary)" }}>{title}</p>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "#9ca3af" }}>{subtext}</p>
            </div>
            <button onClick={onClose} className="fm-btn fm-btn-ghost fm-btn-sm" style={{ padding: "4px 8px", fontSize: 16, lineHeight: 1 }}>×</button>
          </div>

          {/* Pending message preview */}
          {pendingMessage && (
            <div style={{ marginTop: 10, background: "rgba(59,130,246,0.06)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 8, padding: "7px 10px" }}>
              <p style={{ margin: 0, fontSize: 11, color: "#6b7280", marginBottom: 2 }}>Permintaan kamu:</p>
              <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-primary)", fontStyle: "italic" }}>
                "{pendingMessage.length > 80 ? pendingMessage.slice(0, 80) + "…" : pendingMessage}"
              </p>
            </div>
          )}
        </div>

        {/* Breadcrumb + toolbar */}
        <div style={{ padding: "8px 16px", borderBottom: "1px solid rgba(128,128,128,0.08)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 2, flexWrap: "wrap" }}>
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.path} style={{ display: "flex", alignItems: "center", gap: 2 }}>
                {i > 0 && <span style={{ color: "#d1d5db", fontSize: 12 }}>›</span>}
                <button
                  className={`fm-crumb${i === breadcrumbs.length - 1 ? " active" : ""}`}
                  onClick={() => loadDirectory(crumb.path)}
                >{crumb.name}</button>
              </span>
            ))}
          </div>
          <button
            className="fm-btn fm-btn-ghost fm-btn-sm"
            onClick={() => { setShowNewFolder(v => !v); setFolderError(""); setNewFolderName(""); }}
          >+ Folder Baru</button>
        </div>

        {/* New folder input */}
        {showNewFolder && (
          <div style={{ padding: "8px 16px", borderBottom: "1px solid rgba(128,128,128,0.08)", display: "flex", gap: 8, alignItems: "flex-start" }}>
            <div style={{ flex: 1 }}>
              <input
                className="fm-input"
                autoFocus
                placeholder="Nama folder baru..."
                value={newFolderName}
                onChange={e => { setNewFolderName(e.target.value); setFolderError(""); }}
                onKeyDown={e => { if (e.key === "Enter") handleCreateFolder(); if (e.key === "Escape") setShowNewFolder(false); }}
              />
              {folderError && <p style={{ margin: "4px 0 0", fontSize: 11, color: "#ef4444" }}>{folderError}</p>}
            </div>
            <button className="fm-btn fm-btn-primary fm-btn-sm" onClick={handleCreateFolder}>Buat</button>
            <button className="fm-btn fm-btn-ghost fm-btn-sm" onClick={() => setShowNewFolder(false)}>Batal</button>
          </div>
        )}

        {/* File list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
          {loading && (
            <div style={{ textAlign: "center", padding: "40px 0", color: "#9ca3af", fontSize: 13 }}>
              <div style={{ marginBottom: 8, fontSize: 24 }}>⏳</div>Memuat...
            </div>
          )}
          {error && (
            <div style={{ padding: 16, color: "#ef4444", fontSize: 13, textAlign: "center" }}>
              <div style={{ fontSize: 24, marginBottom: 6 }}>⚠️</div>{error}
            </div>
          )}
          {!loading && !error && items.length === 0 && (
            <div style={{ textAlign: "center", padding: "40px 0", color: "#9ca3af", fontSize: 13 }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>📭</div>
              Folder ini kosong
              {mode === "save_new" && <p style={{ fontSize: 12, marginTop: 4 }}>Buat folder baru di sini</p>}
            </div>
          )}
          {!loading && !error && items.map(item => (
            <div
              key={item.path}
              className={`fm-item${item.type === "folder" ? " folder" : ""}${selectedItem?.path === item.path ? " selected" : ""}`}
              style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 10px", borderRadius: 6, userSelect: "none" }}
              onClick={() => {
                if (item.type === "folder" && mode !== "browse") {
                  // save_new: klik folder = navigasi masuk
                  loadDirectory(item.path);
                } else {
                  setSelectedItem(selectedItem?.path === item.path ? null : item);
                }
              }}
              onDoubleClick={() => {
                if (item.type === "folder") loadDirectory(item.path);
              }}
            >
              <span style={{ fontSize: 18, flexShrink: 0 }}>{getIcon(item)}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ margin: 0, fontSize: 13, fontWeight: item.type === "folder" ? 500 : 400, color: "var(--color-text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.name}</p>
                {item.modified && <p style={{ margin: 0, fontSize: 11, color: "#9ca3af" }}>{item.modified}{item.size ? " · " + formatSize(item.size) : ""}</p>}
              </div>
              {item.type === "folder" && (
                <span style={{ fontSize: 12, color: "#d1d5db" }}>›</span>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{ padding: "12px 16px", borderTop: "1px solid rgba(128,128,128,0.12)", background: "rgba(128,128,128,0.03)" }}>

          {/* Save_new: nama project input */}
          {mode === "save_new" && (
            <div style={{ marginBottom: 10 }}>
              <label style={{ display: "block", fontSize: 11, color: "#9ca3af", marginBottom: 4 }}>
                Nama project / folder baru
              </label>
              <input
                ref={inputRef}
                className="fm-input"
                placeholder="contoh: app-kasir, toko-online..."
                value={newProjectName}
                onChange={e => { setNewProjectName(e.target.value); setNameError(""); }}
                onKeyDown={e => { if (e.key === "Enter") handleConfirm(); }}
              />
              {nameError && <p style={{ margin: "4px 0 0", fontSize: 11, color: "#ef4444" }}>{nameError}</p>}
              <p style={{ margin: "4px 0 0", fontSize: 11, color: "#9ca3af" }}>
                Lokasi: <code style={{ fontSize: 11 }}>{currentPath || "workspace"}/{newProjectName || "..."}</code>
              </p>
            </div>
          )}

          {/* Browse mode: tampilkan path yang dipilih */}
          {mode === "browse" && selectedItem && (
            <p style={{ margin: "0 0 8px", fontSize: 12, color: "#6b7280" }}>
              Dipilih: <code style={{ fontSize: 11, background: "rgba(128,128,128,0.1)", padding: "1px 6px", borderRadius: 4 }}>{selectedItem.path}</code>
            </p>
          )}

          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <button className="fm-btn fm-btn-ghost" onClick={onClose}>Batal</button>
            <button
              className="fm-btn fm-btn-primary"
              onClick={handleConfirm}
              disabled={mode === "browse" && !selectedItem}
              style={{ opacity: mode === "browse" && !selectedItem ? 0.5 : 1 }}
            >{confirmLabel}</button>
          </div>
        </div>
      </div>
    </div>
  );
}
