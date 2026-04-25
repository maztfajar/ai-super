import { useState, useRef, useCallback } from "react";

const SUPPORTED_TYPES = {
  "application/pdf": { label: "PDF", icon: "📄" },
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": { label: "DOCX", icon: "📝" },
  "application/msword": { label: "DOC", icon: "📝" },
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": { label: "XLSX", icon: "📊" },
  "application/vnd.ms-excel": { label: "XLS", icon: "📊" },
  "text/plain": { label: "TXT", icon: "📃" },
  "text/csv": { label: "CSV", icon: "📊" },
  "text/markdown": { label: "MD", icon: "📝" },
  "image/png": { label: "PNG", icon: "🖼️" },
  "image/jpeg": { label: "JPG", icon: "🖼️" },
  "image/webp": { label: "WEBP", icon: "🖼️" },
};

export function useChatFileHandler() {
  const [attachedFiles, setAttachedFiles] = useState([]); // file sementara, BUKAN RAG
  const [isDragOver, setIsDragOver] = useState(false);
  const [fileError, setFileError] = useState(null);
  const dragCounter = useRef(0);

  // Validasi & baca file sebagai base64 (hanya untuk sesi chat ini)
  const processFile = useCallback((file) => {
    return new Promise((resolve, reject) => {
      // Determine file extension as fallback if type is empty
      const extMatch = file.name.match(/\.([^.]+)$/);
      const ext = extMatch ? extMatch[1].toLowerCase() : "";
      
      let mimeType = file.type;
      
      // Patch missing mime types for markdown
      if (!mimeType && ext === 'md') {
        mimeType = "text/markdown";
      } else if (!mimeType && ext === 'csv') {
        mimeType = "text/csv";
      }

      if (!SUPPORTED_TYPES[mimeType]) {
        reject(`Tipe file "${mimeType || ext}" tidak didukung.`);
        return;
      }
      if (file.size > 20 * 1024 * 1024) { // maks 20MB
        reject(`File "${file.name}" terlalu besar (maks 20MB).`);
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        resolve({
          id: `file_${Date.now()}_${Math.random().toString(36).slice(2)}`,
          name: file.name,
          type: mimeType,
          size: file.size,
          base64: e.target.result.split(",")[1], // base64 murni
          dataUrl: e.target.result,
          meta: SUPPORTED_TYPES[mimeType],
          isRAG: false, // PENTING: tandai bukan RAG
          sessionOnly: true, // hanya untuk sesi ini
        });
      };
      reader.onerror = () => reject(`Gagal membaca file "${file.name}".`);
      reader.readAsDataURL(file);
    });
  }, []);

  const addFiles = useCallback(async (fileList) => {
    setFileError(null);
    const files = Array.from(fileList);
    const results = [];

    for (const file of files) {
      try {
        const processed = await processFile(file);
        results.push(processed);
      } catch (err) {
        setFileError(err);
      }
    }

    if (results.length > 0) {
      setAttachedFiles((prev) => [...prev, ...results]);
    }
  }, [processFile]);

  const removeFile = useCallback((fileId) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId));
  }, []);

  const clearFiles = useCallback(() => {
    setAttachedFiles([]);
    setFileError(null);
  }, []);

  // Drag & Drop handlers
  const handleDragEnter = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      // Pastikan ada item yang di-drag
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setIsDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = "copy";
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    dragCounter.current = 0;

    const { files } = e.dataTransfer;
    if (files && files.length > 0) {
      addFiles(files);
    }
  }, [addFiles]);

  return {
    attachedFiles,
    isDragOver,
    fileError,
    addFiles,
    removeFile,
    clearFiles,
    dragHandlers: {
      onDragEnter: handleDragEnter,
      onDragLeave: handleDragLeave,
      onDragOver: handleDragOver,
      onDrop: handleDrop,
    },
  };
}
