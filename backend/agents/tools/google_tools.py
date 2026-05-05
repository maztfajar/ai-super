"""
GOG CLI — Google Ecosystem Tools
=================================
Kumpulan tool yang memungkinkan AI agent mengoperasikan ekosistem Google:
- Gmail: baca & kirim email
- Google Calendar: buat & daftar event
- Google Sheets: baca & tulis data
- Google Drive: list & cari file
"""

import json
import structlog
from pathlib import Path
from typing import Optional

log = structlog.get_logger()

GOOGLE_TOKEN_FILE = Path(__file__).parent.parent.parent.parent / ".google_token.json"
GOOGLE_CREDENTIALS_FILE = Path(__file__).parent.parent.parent.parent / ".google_credentials.json"

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.events',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def _get_google_creds():
    """Memuat dan me-refresh kredensial Google OAuth 2.0."""
    if not GOOGLE_TOKEN_FILE.exists():
        raise RuntimeError(
            "GOG CLI belum terotorisasi. Hubungkan akun Google terlebih dahulu melalui menu Integrations."
        )

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    token_data = json.loads(GOOGLE_TOKEN_FILE.read_text())
    creds = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes'),
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Simpan token baru hasil refresh
        updated = {
            'token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': creds.scopes,
        }
        GOOGLE_TOKEN_FILE.write_text(json.dumps(updated))

    return creds


# ── Gmail ─────────────────────────────────────────────────────

async def gog_read_emails(query: str = "is:unread", max_results: int = 10) -> dict:
    """
    Baca email dari Gmail.
    - query: filter Gmail (contoh: 'from:bos@perusahaan.com is:unread')
    - max_results: maksimal jumlah email yang diambil
    """
    try:
        from googleapiclient.discovery import build
        import asyncio

        creds = _get_google_creds()

        def _fetch():
            service = build('gmail', 'v1', credentials=creds)
            results = service.users().messages().list(
                userId='me', q=query, maxResults=max_results
            ).execute()
            messages = results.get('messages', [])

            emails = []
            for msg in messages:
                detail = service.users().messages().get(
                    userId='me', id=msg['id'], format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                headers = {h['name']: h['value'] for h in detail.get('payload', {}).get('headers', [])}
                snippet = detail.get('snippet', '')
                emails.append({
                    'id': msg['id'],
                    'from': headers.get('From', ''),
                    'subject': headers.get('Subject', '(Tanpa Judul)'),
                    'date': headers.get('Date', ''),
                    'snippet': snippet[:300],
                })
            return emails

        emails = await asyncio.get_event_loop().run_in_executor(None, _fetch)
        return {"status": "ok", "count": len(emails), "emails": emails}

    except Exception as e:
        log.error("gog_read_emails error", error=str(e))
        return {"status": "error", "message": str(e)}


async def gog_send_email(to: str, subject: str, body: str) -> dict:
    """
    Kirim email dari Gmail.
    - to: alamat email penerima
    - subject: judul email
    - body: isi pesan (plain text)
    """
    try:
        from googleapiclient.discovery import build
        import base64
        from email.mime.text import MIMEText
        import asyncio

        creds = _get_google_creds()

        def _send():
            service = build('gmail', 'v1', credentials=creds)
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(
                userId='me', body={'raw': raw}
            ).execute()

        await asyncio.get_event_loop().run_in_executor(None, _send)
        return {"status": "ok", "message": f"Email berhasil dikirim ke {to}"}

    except Exception as e:
        log.error("gog_send_email error", error=str(e))
        return {"status": "error", "message": str(e)}


# ── Google Calendar ───────────────────────────────────────────

async def gog_create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    attendees: Optional[list] = None
) -> dict:
    """
    Buat event di Google Calendar.
    - summary: judul event
    - start_time: waktu mulai dalam format ISO 8601 (contoh: '2025-06-01T10:00:00+07:00')
    - end_time: waktu selesai dalam format ISO 8601
    - description: deskripsi event (opsional)
    - attendees: list email peserta (opsional)
    """
    try:
        from googleapiclient.discovery import build
        import asyncio

        creds = _get_google_creds()

        def _create():
            service = build('calendar', 'v3', credentials=creds)
            event_body = {
                'summary': summary,
                'description': description,
                'start': {'dateTime': start_time},
                'end': {'dateTime': end_time},
            }
            if attendees:
                event_body['attendees'] = [{'email': e} for e in attendees]

            event = service.events().insert(calendarId='primary', body=event_body).execute()
            return event.get('htmlLink', '')

        link = await asyncio.get_event_loop().run_in_executor(None, _create)
        return {"status": "ok", "message": f"Event '{summary}' berhasil dibuat!", "event_link": link}

    except Exception as e:
        log.error("gog_create_calendar_event error", error=str(e))
        return {"status": "error", "message": str(e)}


async def gog_list_calendar_events(max_results: int = 10) -> dict:
    """Ambil daftar event mendatang dari Google Calendar."""
    try:
        from googleapiclient.discovery import build
        import asyncio
        from datetime import datetime, timezone

        creds = _get_google_creds()

        def _list():
            service = build('calendar', 'v3', credentials=creds)
            now = datetime.now(timezone.utc).isoformat()
            result = service.events().list(
                calendarId='primary', timeMin=now,
                maxResults=max_results, singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = result.get('items', [])
            return [
                {
                    'summary': e.get('summary', '(Tanpa Judul)'),
                    'start': e.get('start', {}).get('dateTime', e.get('start', {}).get('date', '')),
                    'end': e.get('end', {}).get('dateTime', e.get('end', {}).get('date', '')),
                    'link': e.get('htmlLink', ''),
                }
                for e in events
            ]

        events = await asyncio.get_event_loop().run_in_executor(None, _list)
        return {"status": "ok", "count": len(events), "events": events}

    except Exception as e:
        log.error("gog_list_calendar_events error", error=str(e))
        return {"status": "error", "message": str(e)}


# ── Google Sheets ─────────────────────────────────────────────

async def gog_read_sheet(spreadsheet_id: str, range_name: str = "Sheet1!A1:Z100") -> dict:
    """
    Baca data dari Google Sheets.
    - spreadsheet_id: ID spreadsheet dari URL (bagian antara /d/ dan /edit)
    - range_name: range dalam format A1 (contoh: 'Sheet1!A1:E10')
    """
    try:
        from googleapiclient.discovery import build
        import asyncio

        creds = _get_google_creds()

        def _read():
            service = build('sheets', 'v4', credentials=creds)
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name
            ).execute()
            return result.get('values', [])

        values = await asyncio.get_event_loop().run_in_executor(None, _read)
        return {"status": "ok", "rows": len(values), "data": values}

    except Exception as e:
        log.error("gog_read_sheet error", error=str(e))
        return {"status": "error", "message": str(e)}


async def gog_append_sheet_row(spreadsheet_id: str, values: list, range_name: str = "Sheet1!A1") -> dict:
    """
    Tambah baris data ke Google Sheets.
    - spreadsheet_id: ID spreadsheet
    - values: list data untuk satu baris (contoh: ['Nama', 'Email', 'Status'])
    - range_name: range awal penambahan
    """
    try:
        from googleapiclient.discovery import build
        import asyncio

        creds = _get_google_creds()

        def _append():
            service = build('sheets', 'v4', credentials=creds)
            body = {'values': [values]}
            result = service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            return result.get('updates', {}).get('updatedRows', 0)

        rows = await asyncio.get_event_loop().run_in_executor(None, _append)
        return {"status": "ok", "message": f"{rows} baris berhasil ditambahkan ke Sheets."}

    except Exception as e:
        log.error("gog_append_sheet_row error", error=str(e))
        return {"status": "error", "message": str(e)}


# ── Google Drive ──────────────────────────────────────────────

async def gog_list_drive_files(query: str = "", max_results: int = 20) -> dict:
    """
    Cari dan daftarkan file dari Google Drive.
    - query: filter pencarian Drive (contoh: "name contains 'laporan' and mimeType='application/pdf'")
    - max_results: maksimal jumlah file yang ditampilkan
    """
    try:
        from googleapiclient.discovery import build
        import asyncio

        creds = _get_google_creds()

        def _list():
            service = build('drive', 'v3', credentials=creds)
            params = {
                'pageSize': max_results,
                'fields': "nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink, size)",
            }
            if query:
                params['q'] = query

            result = service.files().list(**params).execute()
            files = result.get('files', [])
            return [
                {
                    'id': f['id'],
                    'name': f['name'],
                    'type': f.get('mimeType', ''),
                    'modified': f.get('modifiedTime', ''),
                    'link': f.get('webViewLink', ''),
                    'size': f.get('size', 'N/A'),
                }
                for f in files
            ]

        files = await asyncio.get_event_loop().run_in_executor(None, _list)
        return {"status": "ok", "count": len(files), "files": files}

    except Exception as e:
        log.error("gog_list_drive_files error", error=str(e))
        return {"status": "error", "message": str(e)}


# ── Tool Registry Definitions ─────────────────────────────────

GOOGLE_TOOLS = [
    {
        "name": "gog_read_emails",
        "fn": gog_read_emails,
        "description": "Baca email dari Gmail berdasarkan query. Gunakan untuk memeriksa email baru, mencari email dari pengirim tertentu, dll.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Filter Gmail (contoh: 'is:unread', 'from:boss@company.com')"},
                "max_results": {"type": "integer", "description": "Maksimal email yang diambil (default: 10)"}
            }
        }
    },
    {
        "name": "gog_send_email",
        "fn": gog_send_email,
        "description": "Kirim email melalui Gmail.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Alamat email penerima"},
                "subject": {"type": "string", "description": "Judul email"},
                "body": {"type": "string", "description": "Isi pesan email"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "gog_create_calendar_event",
        "fn": gog_create_calendar_event,
        "description": "Buat jadwal/event baru di Google Calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Judul event"},
                "start_time": {"type": "string", "description": "Waktu mulai ISO 8601 (contoh: '2025-06-01T10:00:00+07:00')"},
                "end_time": {"type": "string", "description": "Waktu selesai ISO 8601"},
                "description": {"type": "string", "description": "Deskripsi event (opsional)"},
                "attendees": {"type": "array", "items": {"type": "string"}, "description": "List email peserta (opsional)"}
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "gog_list_calendar_events",
        "fn": gog_list_calendar_events,
        "description": "Ambil daftar event mendatang dari Google Calendar.",
        "parameters": {
            "type": "object",
            "properties": {
                "max_results": {"type": "integer", "description": "Maksimal event yang ditampilkan (default: 10)"}
            }
        }
    },
    {
        "name": "gog_read_sheet",
        "fn": gog_read_sheet,
        "description": "Baca data dari Google Sheets. Gunakan untuk mengambil data dari spreadsheet.",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "ID spreadsheet dari URL Google Sheets"},
                "range_name": {"type": "string", "description": "Range dalam format A1 (contoh: 'Sheet1!A1:E10')"}
            },
            "required": ["spreadsheet_id"]
        }
    },
    {
        "name": "gog_append_sheet_row",
        "fn": gog_append_sheet_row,
        "description": "Tambah baris data baru ke Google Sheets.",
        "parameters": {
            "type": "object",
            "properties": {
                "spreadsheet_id": {"type": "string", "description": "ID spreadsheet"},
                "values": {"type": "array", "items": {"type": "string"}, "description": "Data untuk satu baris (contoh: ['Nama', 'Email', 'Status'])"},
                "range_name": {"type": "string", "description": "Range tujuan (default: 'Sheet1!A1')"}
            },
            "required": ["spreadsheet_id", "values"]
        }
    },
    {
        "name": "gog_list_drive_files",
        "fn": gog_list_drive_files,
        "description": "Cari dan daftarkan file dari Google Drive.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Filter pencarian (contoh: \"name contains 'laporan'\")"},
                "max_results": {"type": "integer", "description": "Maksimal file yang ditampilkan (default: 20)"}
            }
        }
    },
]
