import os
import json
import base64
from typing import Optional
import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

log = structlog.get_logger()

SCOPES = ['https://www.googleapis.com/auth/drive']

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

async def upload_to_drive(filename: str, content: str) -> str:
    """Upload a text file to Google Drive. Returns the file ID or an error message."""
    service = get_drive_service()
    if not service:
        return "Error: Google Drive Authentication failed or credentials not provided. User needs to set GOOGLE_DRIVE_CREDENTIALS."
        
    try:
        file_metadata = {'name': filename}
        
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
            
        # Write content to in-memory bytes buffer
        fh = io.BytesIO(content.encode("utf-8"))
        media = MediaIoBaseUpload(fh, mimetype=mimetype, resumable=True)
        
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink'
        ).execute()
        
        link = file.get("webViewLink", "N/A")
        return f"Successfully created file '{filename}'. Drive File ID: {file.get('id')}\nAccess Link: {link}"
    except Exception as e:
        log.error("Drive upload error", error=str(e))
        return f"Error uploading to Google Drive: {str(e)}"

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
            fields="nextPageToken, files(id, name)",
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
