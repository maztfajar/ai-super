/**
 * Clipboard utility yang bekerja di semua konteks (HTTP, HTTPS, localhost).
 * navigator.clipboard.writeText() hanya bekerja di secure context (HTTPS/localhost).
 * Fallback menggunakan document.execCommand('copy') untuk HTTP.
 */
export function copyToClipboard(text) {
  // Coba modern Clipboard API dulu
  if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
    return navigator.clipboard.writeText(text).catch(() => fallbackCopy(text))
  }
  // Fallback langsung
  return fallbackCopy(text)
}

function fallbackCopy(text) {
  return new Promise((resolve, reject) => {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '-9999px'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    try {
      const ok = document.execCommand('copy')
      document.body.removeChild(textarea)
      if (ok) resolve()
      else reject(new Error('execCommand copy failed'))
    } catch (e) {
      document.body.removeChild(textarea)
      reject(e)
    }
  })
}
