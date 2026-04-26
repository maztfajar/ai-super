"""
ProcessEmitter — Structured Process Step Events
Menghasilkan event SSE bertipe 'process' dengan struktur standar:
  { action, detail, count, ts, [code], [language] }

Digunakan oleh Executor dan Orchestrator untuk mengirim
progress step yang terstruktur ke frontend.
"""
import time
import json


# ── Canonical action labels ───────────────────────────────────────
VALID_ACTIONS = {
    "Thinking", "Worked", "Explored", "Ran", "Edited", "Analyzed",
    "Thought", "Modify", "Reading", "Writing", "Written",
    "Listed", "Searched", "Fetched", "Created", "Deleted",
    "Moved", "Copied", "Planned", "Summarized", "Checked",
    "Found", "Error", "Done",
}

# Sentinel prefix — travels through plain-text chunk stream
PROCESS_EVENT_PREFIX = "\x00PROC\x00"


class ProcessEmitter:
    """
    Utility untuk membuat payload SSE process event.
    Gunakan .to_sse()      → string SSE langsung ke client.
    Gunakan .to_sentinel() → string melewati chunk stream
                             (orchestrator forward sebagai process event).
    Extra fields (code, language) digunakan untuk membawa konten
    file yang ditulis agent agar frontend bisa tampilkan artifact.
    """

    def make(
        self,
        action: str,
        detail: str = "",
        count: int = None,
        extra: dict = None,
    ) -> dict:
        """Buat payload process event."""
        payload = {
            "action": action,
            "detail": detail,
            "count": count,
            "ts": time.time(),
        }
        if extra:
            payload.update(extra)
        return payload

    def to_sse(
        self,
        action: str,
        detail: str = "",
        count: int = None,
        extra: dict = None,
    ) -> str:
        """Buat SSE string untuk dikirim langsung ke client."""
        payload = {
            "type": "process",
            **self.make(action, detail, count, extra),
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def to_sentinel(
        self,
        action: str,
        detail: str = "",
        count: int = None,
        extra: dict = None,
    ) -> str:
        """
        Buat string sentinel yang bisa lewat chunk stream.
        Format: \x00PROC\x00{json_payload}
        """
        payload = self.make(action, detail, count, extra)
        return PROCESS_EVENT_PREFIX + json.dumps(payload, ensure_ascii=False)


# Singleton
process_emitter = ProcessEmitter()
