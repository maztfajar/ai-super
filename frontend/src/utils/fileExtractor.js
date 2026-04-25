// utils/fileExtractor.js
// Ekstrak teks dari berbagai format file TANPA menyimpan ke RAG

/**
 * Ekstrak konten dari file untuk dikirim ke AI dalam konteks chat.
 * File TIDAK disimpan ke database / RAG.
 */
export async function extractFileContent(file) {
  const { type, base64, name, dataUrl } = file;

  // PDF → gunakan pdf.js
  if (type === "application/pdf") {
    return await extractPDF(base64, name);
  }

  // Excel XLSX/XLS → gunakan SheetJS
  if (
    type === "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ||
    type === "application/vnd.ms-excel"
  ) {
    return await extractExcel(base64, name);
  }

  // CSV / Text
  if (type === "text/csv" || type === "text/plain" || type === "text/markdown") {
    return await extractText(base64, name);
  }

  // DOCX → gunakan mammoth
  if (
    type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    type === "application/msword"
  ) {
    return await extractDOCX(base64, name);
  }

  // Gambar → kembalikan sebagai image untuk vision AI
  if (type.startsWith("image/")) {
    return { type: "image", dataUrl, base64, mime_type: type, name };
  }

  return { type: "unknown", text: `File: ${name} (tidak dapat diekstrak, format tidak didukung)`, name };
}

async function extractPDF(base64, name) {
  try {
    const pdfjsLib = await import("pdfjs-dist");
    pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

    const pdf = await pdfjsLib.getDocument({ data: bytes }).promise;
    let fullText = "";

    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      fullText += content.items.map((item) => item.str).join(" ") + "\n";
    }

    return { type: "text", text: fullText.trim(), name, pages: pdf.numPages };
  } catch (err) {
    return { type: "error", text: `Gagal membaca PDF "${name}": ${err.message}`, name };
  }
}

async function extractExcel(base64, name) {
  try {
    const XLSX = await import("xlsx");
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

    const workbook = XLSX.read(bytes, { type: "array" });
    let result = "";

    workbook.SheetNames.forEach((sheetName) => {
      const sheet = workbook.Sheets[sheetName];
      const csv = XLSX.utils.sheet_to_csv(sheet);
      result += `=== Sheet: ${sheetName} ===\n${csv}\n\n`;
    });

    return { type: "text", text: result.trim(), name, sheets: workbook.SheetNames };
  } catch (err) {
    return { type: "error", text: `Gagal membaca Excel "${name}": ${err.message}`, name };
  }
}

async function extractDOCX(base64, name) {
  try {
    const mammoth = await import("mammoth");
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

    const result = await mammoth.extractRawText({ arrayBuffer: bytes.buffer });
    return { type: "text", text: result.value.trim(), name };
  } catch (err) {
    return { type: "error", text: `Gagal membaca DOCX "${name}": ${err.message}`, name };
  }
}

async function extractText(base64, name) {
  try {
    const text = decodeURIComponent(escape(window.atob(base64))); // Handle unicode properly
    return { type: "text", text: text.trim(), name };
  } catch (err) {
    // Fallback if decodeURIComponent fails
    try {
      const text = atob(base64);
      return { type: "text", text: text.trim(), name };
    } catch(e) {
      return { type: "error", text: `Gagal membaca file teks "${name}": ${err.message}`, name };
    }
  }
}
