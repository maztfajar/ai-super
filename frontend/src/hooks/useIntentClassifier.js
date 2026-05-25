// hooks/useIntentClassifier.js
// Panggil ini di komponen Chat utama sebelum kirim pesan ke orchestra

import { useState, useCallback } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

/**
 * Hook untuk klasifikasi intent dan manajemen state file manager popup.
 *
 * Cara pakai di Chat.jsx:
 *
 *   const { classifyAndHandle, fileManagerState, closeFileManager } = useIntentClassifier();
 *
 *   const handleSend = async (message) => {
 *     const shouldProceed = await classifyAndHandle(message);
 *     if (shouldProceed) {
 *       await sendToOrchestra(message);  // lanjut normal
 *     }
 *     // kalau false → popup sudah terbuka, tunggu user pilih lokasi
 *   };
 */
export function useIntentClassifier() {
  const [fileManagerState, setFileManagerState] = useState({
    isOpen: false,
    mode: null,           // "browse" | "save_new"
    pendingMessage: null, // pesan user yang di-hold
    intent: null,
  });

  const closeFileManager = useCallback(() => {
    setFileManagerState({
      isOpen: false,
      mode: null,
      pendingMessage: null,
      intent: null,
    });
  }, []);

  /**
   * Klasifikasikan intent lalu putuskan apakah perlu popup atau lanjut normal.
   *
   * @returns {Promise<boolean>} true = lanjut proses normal, false = popup dibuka
   */
  const classifyAndHandle = useCallback(async (message, onProceed) => {
    // ── Fast-path pre-check on frontend ──
    const msg = (message || "").toLowerCase().trim();
    
    // Kata kunci yang mungkin membutuhkan popup (app building / file operations)
    const technicalKeywords = [
      'app', 'aplikasi', 'website', 'web', 'dashboard', 'api', 'backend', 'frontend', 'proyek', 'project',
      'file', 'folder', 'direktori', 'directory', 'coding', 'setup', 'build', 'create', 'create-vite', 'react', 'nextjs',
      'edit', 'buka', 'open', 'simpan', 'save', 'modify', 'delete', 'hapus', 'ganti nama', 'rename'
    ];
    
    // Kata kunci yang bersifat deskriptif / penulisan (tidak butuh popup)
    const nonPopupKeywords = [
      'berita', 'artikel', 'cerita', 'puisi', 'pantun', 'dongeng', 'gambar', 'image', 'suara', 'audio', 
      'ringkas', 'terjemah', 'laporan', 'caption', 'konten', 'post', 'email', 'surat', 'analisis', 'jelaskan'
    ];
    
    const hasTech = technicalKeywords.some(kw => msg.includes(kw));
    const hasNonPopup = nonPopupKeywords.some(kw => msg.includes(kw));
    
    // Jika tidak mengandung keyword teknis, atau mengandung keyword penulisan tanpa merujuk ke file/folder spesifik
    if (!hasTech || (hasNonPopup && !msg.includes('file') && !msg.includes('folder') && !msg.includes('aplikasi') && !msg.includes('app') && !msg.includes('project') && !msg.includes('proyek'))) {
      return true; // Lanjut kirim pesan secara instan (0ms delay)
    }

    try {
      const res = await fetch(`${API_BASE}/file-manager/classify-intent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      if (!res.ok) throw new Error("Classify failed");

      const result = await res.json();

      if (result.needs_popup) {
        // Simpan pesan, buka popup
        setFileManagerState({
          isOpen: true,
          mode: result.popup_mode,       // "browse" atau "save_new"
          pendingMessage: message,
          intent: result.intent,
        });
        return false; // tahan dulu, jangan kirim ke orchestra
      }

      // Tidak perlu popup — lanjut langsung
      return true;

    } catch (err) {
      console.error("[useIntentClassifier] Error:", err);
      return true; // kalau classifier gagal, lanjut saja (fail-safe)
    }
  }, []);

  /**
   * Dipanggil setelah user memilih lokasi di popup.
   * Lanjutkan pesan ke orchestra dengan info lokasi.
   */
  const confirmAndProceed = useCallback(async (selectedPath, onProceed) => {
    const { pendingMessage, intent } = fileManagerState;

    closeFileManager();

    if (onProceed && pendingMessage) {
      // Kirim ke orchestra dengan context lokasi
      const enrichedMessage = intent === "BUILD_APP"
        ? `${pendingMessage}\n\n[SYSTEM: Simpan project ke direktori: ${selectedPath}]`
        : `${pendingMessage}\n\n[SYSTEM: File yang akan diedit: ${selectedPath}]`;

      await onProceed(enrichedMessage);
    }
  }, [fileManagerState, closeFileManager]);

  return {
    classifyAndHandle,
    confirmAndProceed,
    closeFileManager,
    fileManagerState,
    isPopupOpen: fileManagerState.isOpen,
  };
}
