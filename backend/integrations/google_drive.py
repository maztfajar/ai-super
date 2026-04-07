import os
import json
import base64
from typing import Optional, Union
import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import io

from core.config import settings

log = structlog.get_logger()

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_service_account_email() -> str:
    """Mengambil email service account dari credentials."""
    creds_str = os.environ.get("GOOGLE_DRIVE_CREDENTIALS", "")
    if creds_str:
        try:
            if creds_str.strip().startswith("{"):
                return json.loads(creds_str).get("client_email", "Email Service Account")
            else:
                return json.loads(base64.b64decode(creds_str).decode("utf-8")).get("client_email", "Email Service Account")
        except:
            pass
    return "Email Service Account"

def get_drive_service():
    """Build and return a Google Drive API service using credentials from environment."""
    creds_str = os.environ.get("GOOGLE_DRIVE_CREDENTIALS", "")
    if not creds_str:
        return None
        
    try:
        creds_info = {}
        if creds_str.strip().startswith("{"):
            creds_info = json.loads(creds_str)
        else:
            decoded = base64.b64decode(creds_str).decode("utf-8")
            creds_info = json.loads(decoded)
            
        if "web" in creds_info or "installed" in creds_info:
            log.error("Google Drive: Kredensial yang dimasukkan adalah OAuth Client ID, bukan Service Account JSON.")
            return None

        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)
        return service
    except json.JSONDecodeError:
        log.error("Failed to parse Google Drive credentials: Not a valid JSON.")
        return None
    except Exception as e:
        log.error("Failed to initialize Google Drive service", error=str(e), keys=list(creds_info.keys()) if isinstance(creds_info, dict) else [])
        return None

async def create_drive_folder(folder_name: str, parent_id: Optional[str] = None) -> str:
    """Create a new folder in Google Drive. Returns folder ID."""
    service = get_drive_service()
    if not service:
        raise Exception("Google Drive Authentication failed or credentials not provided.")
    
    try:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        file = service.files().create(body=file_metadata, fields='id').execute()
        return file.get('id')
    except HttpError as e:
        if e.resp.status in [403, 400] and "storage quota" in str(e).lower():
            email = get_service_account_email()
            raise Exception(f"LIMITASI GOOGLE: Service Account tidak punya kuota Drive sendiri. SOLUSI: 1. Buat folder di akun Google Drive pribadi Anda. 2. Share/Bagikan folder tersebut ke email '{email}' (sebagai Editor). 3. Pilih folder yang sudah di-share tersebut di daftar ini.")
        log.error("Drive create folder error", error=str(e))
        raise Exception(f"Failed to create Google Drive folder: {str(e)}")
    except Exception as e:
        log.error("Drive create folder error", error=str(e))
        raise Exception(f"Failed to create Google Drive folder: {str(e)}")

async def upload_to_drive(filename: str, content: Union[str, bytes], folder_id: Optional[str] = None) -> dict:
    """Upload a file to Google Drive. Returns a dict with status, id, and webViewLink."""
    service = get_drive_service()
    if not service:
        return {"status": "error", "message": "Google Drive Authentication failed or credentials not provided."}
        
    try:
        # Gunakan folder default dari settings jika tidak ada folder_id eksplisit
        target_folder = folder_id or settings.GDRIVE_UPLOAD_FOLDER_ID or os.environ.get("GDRIVE_UPLOAD_FOLDER_ID", "")
        
        file_metadata = {'name': filename}
        if target_folder:
            file_metadata['parents'] = [target_folder]
        else:
            # Service Account TIDAK punya kuota Drive sendiri
            email = get_service_account_email()
            log.warning(
                "Upload tanpa folder ID — Service Account tidak punya kuota sendiri",
                hint=f"Share folder Drive ke {email}, lalu set GDRIVE_UPLOAD_FOLDER_ID di Integrasi.",
            )
        
        # Determine mime type based on extension
        mimetype = 'text/plain'
        if filename.endswith(".html"):
            mimetype = 'text/html'
        elif filename.endswith(".md"):
            mimetype = 'text/markdown'
        elif filename.endswith(".csv"):
            mimetype = 'text/csv'
        elif filename.endswith(".json"):
            mimetype = 'application/json'
        elif filename.endswith(".pdf"):
            mimetype = 'application/pdf'
        elif filename.endswith(".docx"):
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif filename.endswith(".xlsx"):
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            
        # Write content to in-memory bytes buffer
        if isinstance(content, str):
            fh = io.BytesIO(content.encode("utf-8"))
        else:
            fh = io.BytesIO(content)
            
        media = MediaIoBaseUpload(fh, mimetype=mimetype, resumable=True)
        
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink'
        ).execute()
        
        link = file.get("webViewLink", "N/A")
        return {"status": "success", "id": file.get('id'), "link": link, "message": f"Successfully created file '{filename}'"}
    except HttpError as e:
        err_str = str(e).lower()
        if e.resp.status in [403, 400] and ("storage quota" in err_str or "storageQuotaExceeded" in str(e)):
            email = get_service_account_email()
            return {
                "status": "error",
                "message": (
                    f"⚠️ LIMITASI GOOGLE: Service Account tidak punya kuota Drive sendiri.\n\n"
                    f"SOLUSI CEPAT:\n"
                    f"1. Buat folder di Google Drive PRIBADI Anda.\n"
                    f"2. Klik kanan folder → Share/Bagikan ke: {email} (sebagai Editor).\n"
                    f"3. Salin Folder ID dari URL (contoh: drive.google.com/drive/folders/XXXXX).\n"
                    f"4. Tempel Folder ID tersebut di menu Integrasi → Google Drive → Folder Tujuan Upload."
                ),
            }
        log.error("Drive upload error", error=str(e))
        return {"status": "error", "message": f"Error uploading to Google Drive: {str(e)}"}
    except Exception as e:
        log.error("Drive upload error", error=str(e))
        return {"status": "error", "message": f"Error uploading to Google Drive: {str(e)}"}

async def list_drive_files(query: str = "") -> str:
    """List recent files in Google Drive."""
    service = get_drive_service()
    if not service:
        return "Error: Google Drive Authentication failed or credentials not provided."
        
    try:
        q = "trashed = false"
        if query:
            q += f" and name contains '{query}'"
            
        results = service.files().list(
            q=q,
            pageSize=10, 
            fields="nextPageToken, files(id, name, mimeType)",
            orderBy="modifiedTime desc"
        ).execute()
        items = results.get('files', [])
        
        if not items:
            return "No files found matching the query."
            
        resp = "Files found in Google Drive:\n"
        for item in items:
            resp += f"- {item['name']} (ID: {item['id']})\n"
        return resp
    except Exception as e:
        log.error("Drive list error", error=str(e))
        return f"Error listing from Google Drive: {str(e)}"

async def list_drive_folders() -> list:
    """List all folders in Google Drive."""
    service = get_drive_service()
    if not service:
        raise Exception("Autentikasi Google Drive gagal atau kredensial belum diatur.")
    try:
        q = "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(
            q=q,
            pageSize=100,
            fields="nextPageToken, files(id, name, parents)",
            orderBy="name"
        ).execute()
        return results.get('files', [])
    except Exception as e:
        log.error("Drive folder list error", error=str(e))
        raise Exception(f"Gagal memuat folder: {str(e)}")

async def list_files_in_folder(folder_id: str) -> list:
    """List all files in a specific Google Drive folder, including file size."""
    service = get_drive_service()
    if not service:
        raise Exception("Autentikasi Google Drive gagal.")
    try:
        q = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(
            q=q,
            pageSize=100,
            # Tambahkan 'size' untuk file regular (Google Workspace files tidak punya 'size')
            fields="nextPageToken, files(id, name, mimeType, size)",
            orderBy="name"
        ).execute()
        files = results.get('files', [])
        log.info("Daftar file Drive diperoleh", folder_id=folder_id, count=len(files))
        return files
    except Exception as e:
        log.error("Drive files list error", error=str(e))
        raise

async def download_from_drive(file_id: str, mime_type: str, dest_path: str, max_retry: int = 2) -> str:
    """
    Download file dari Google Drive.
    - Google Workspace files di-export ke format biasa.
    - Verifikasi file tidak 0 bytes setelah download.
    - Retry otomatis jika gagal.
    Returns file extension (e.g. '.pdf', '.csv').
    """
    service = get_drive_service()
    if not service:
        raise Exception("Autentikasi Google Drive gagal.")

    from googleapiclient.http import MediaIoBaseDownload
    import io

    last_error = None
    for attempt in range(max_retry + 1):
        try:
            final_ext = os.path.splitext(dest_path)[1]

            if mime_type.startswith('application/vnd.google-apps.'):
                # Export Google Workspace documents
                export_mime = 'application/pdf'
                if 'document' in mime_type:
                    export_mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    final_ext = '.docx'
                elif 'spreadsheet' in mime_type:
                    export_mime = 'text/csv'
                    final_ext = '.csv'
                elif 'presentation' in mime_type:
                    export_mime = 'application/pdf'
                    final_ext = '.pdf'
                request = service.files().export_media(fileId=file_id, mimeType=export_mime)
            else:
                request = service.files().get_media(fileId=file_id)

            with io.FileIO(dest_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            # Verifikasi file tidak 0 bytes
            file_size = os.path.getsize(dest_path) if os.path.exists(dest_path) else 0
            if file_size == 0:
                log.warning(
                    "File terunduh tapi 0 bytes",
                    file_id=file_id,
                    attempt=attempt + 1,
                    dest_path=dest_path,
                )
                if attempt < max_retry:
                    import time
                    time.sleep(1)
                    continue
                raise ValueError(f"File terunduh dengan ukuran 0 bytes setelah {max_retry+1} percobaan")

            log.info(
                "Drive download sukses",
                file_id=file_id,
                size_kb=round(file_size / 1024, 1),
                ext=final_ext,
                attempt=attempt + 1,
            )
            return final_ext

        except ValueError:
            raise
        except Exception as e:
            last_error = e
            log.warning(
                "Drive download error, retry",
                file_id=file_id,
                attempt=attempt + 1,
                error=str(e),
            )
            if attempt < max_retry:
                import time
                time.sleep(2 ** attempt)

    log.error("Drive download gagal setelah semua retry", file_id=file_id, error=str(last_error))
    raise last_error
