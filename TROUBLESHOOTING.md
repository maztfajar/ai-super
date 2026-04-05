# Troubleshooting RAG & Sumopod

Panduan ini berisi masalah umum yang mungkin terjadi saat menggunakan fitur RAG (Retrieval-Augmented Generation) dan integrasi Sumopod, beserta solusinya.

## 1. Folder `rag_documents` Tidak Ditemukan
**Gejala:** Saat startup atau scan folder, muncul error folder tidak ditemukan.
**Penyebab:** Folder belum dibuat, atau masalah permission akses folder.
**Solusi:**
Sistem sekarang sudah dilengkapi dengan script auto-setup. Jalankan perintah berikut:
```bash
cd backend
source venv/bin/activate
python scripts/setup_rag.py
```
Script ini akan secara otomatis membuat `/rag_documents`, `/backend/data/chroma_db`, dan `/backend/data/uploads` beserta izin akses yang dibutuhkan.

## 2. Command Timed Out After 120 Seconds / 45 Seconds
**Gejala:** RAG indexing berjalan terus dan akhirnya gagal karena timeout.
**Penyebab:** Memproses dokumen PDF/DOCX yang sangat besar membutuhkan waktu lama, atau server mengalami load tinggi.
**Solusi:**
Sistem sudah dioptimasi untuk async batch processing dengan batas waktu logis (45 detik per file) untuk mencegah pemblokiran. Jika file terlalu besar:
- Pecah PDF menjadi beberapa file lebih kecil (masing-masing < 50 layar/halaman).
- Cek log performa dengan `GET /api/rag/status`.
- Pastikan limit ukuran tidak melebihi `MAX_UPLOAD_SIZE_MB` di `.env` (default 50 MB).

## 3. Data Tidak Ditemukan Walaupun File Sudah Di-scan
**Gejala:** Anda mengunggah file berisi "NIK Meryet", tetapi saat ditanya AI menjawab "Data tidak ditemukan".
**Penyebab:**
- File tidak ter-index dengan benar karena format tidak didukung.
- Dokumen tersebut "kosong" (0 bytes) atau beruba gambar/hasil scan tanpa OCR.
- RAG Vectorstore (ChromaDB) gagal menyimpan embeddings karena masalah koneksi API Sumopod.

**Solusi:**
- Format yg didukung sekarang: `.pdf, .docx, .txt, .csv, .md, .json, .xlsx, .xls, .pptx, .ppt`.
- Untuk file .pdf berupa nota foto/scan (bukan teks ketikan), Anda tetap perlu melewatkannya di proses OCR (misal Google Drive Docs) terlebih dahulu agar teks bisa dibaca.
- Pastikan indexing berhasil dan status bukan `error`.
- Cek koneksi ke Sumopod: `python backend/scripts/test_sumopod_connection.py`.

## 4. Google Drive Sync Selalu Mengunduh File 0KB
**Gejala:** Hasil sinkronisasi Google Drive adalah file kosong 0KB.
**Penyebab:** Masalah permission (Drive API tidak bisa mengakses content file) atau format asli adalah Google Workspace Format yang belum berhasil di-import/export.
**Solusi:**
- Sistem terbaru sekarang secara otomatis melakukan validasi dan retry download. File Google Docs otomatis diekspor sebagai `.docx` atau `.pdf`.
- Apabila masih ada yang error 0 bytes, system akan menampilkan peringatan dan melewatkan file tersebut agar vektor database tidak kotor.
- Pastikan Service Account / Google Credentials Anda memiliki askses *Reader/Viewer* terhadap folder Drive yang disinkronisasi.

## 5. Sumopod Embedding Timeout atau Exception
**Gejala:** Proses Indexing selalu error di log, atau muncul HTTP Error saat menghubungi `https://api.sumopod.com/v1/embeddings`.
**Penyebab:** API Sumopod sedang tidak stabil, rate limit terlampaui, atau format input salah.
**Solusi:**
- Service model `embedding_service.py` sudah dilengkapi dengan *Exponential Backoff*. Jika RAG gagal, sistem akan diulang hingga 3 kali otomatis.
- Cek API Key Anda di `.env`: `SUMOPOD_API_KEY=sk-...`
- Cek Host (base url): `SUMOPOD_HOST=https://ai.sumopod.com/v1`
- UJI KONEKSI SECARA MANUAL:
   ```bash
   cd backend
   python scripts/test_sumopod_connection.py
   ```

## 6. Lupa Cara Menjalankan RAG Scanner Manual
Bila Anda menaruh banyak file sekaligus ke folder project `/rag_documents/` melalui FTP/SFTP dan ingin segera dikenali oleh AI, jalankan Endpoint HTTP ini atau gunakan tombol Scan dari UI yang sudah tersedia di aplikasi.
Endpoint `POST /api/rag/scan-rag-documents` akan mengindeks file baru yang belum terindeks.
