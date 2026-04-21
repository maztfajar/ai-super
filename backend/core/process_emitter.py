"""
ProcessEmitter — Structured Process Step Events
Menghasilkan event SSE bertipe 'process' dengan struktur standar:
  { action, detail, count, ts }

Digunakan oleh Executor dan Orchestrator untuk mengirim
progress step yang terstruktur ke frontend.
"""
import time
import json


# ── Canonical action labels ───────────────────────────────────────
# Pastikan setiap label konsisten agar frontend bisa menampilkan ikon yg tepat
VALID_ACTIONS = {
    "Thinking",
    "Worked",
    "Explored",
    "Ran",
    "Edited",
    "Analyzed",
    "Thought",
    "Modify",
    "Reading",
    "Writing",
    "Listed",
    "Searched",
    "Fetched",
    "Created",
    "Deleted",
    "Moved",
    "Copied",
    "Planned",
    "Summarized",
    "Checked",
    "Found",
    "Error",
    "Done",
}


# Sentinel prefix used when process events must travel through a plain-text stream
# (e.g. AgentExecutor → Orchestrator queue). The orchestrator detects this prefix
# and converts the payload back into a proper OrchestratorEvent.proc().
PROCESS_EVENT_PREFIX = "\x00PROC\x00"


class ProcessEmitter:
    """
    Utility untuk membuat payload SSE process event.
    Tidak langsung yield ke stream — hanya membuat dict payload.
    Gunakan .to_sse() untuk mendapat string SSE langsung ke client.
    Gunakan .to_sentinel() untuk string yang bisa melewati chunk stream
    (orchestrator akan mendeteksi prefix dan forward sebagai process event).
    """

    def make(
        self,
        action: str,
        detail: str = "",
        count: int = None,
    ) -> dict:
        """Buat payload process event."""
        return {
            "action": action,
            "detail": detail,
            "count": count,
            "ts": time.time(),
        }

    def to_sse(
        self,
        action: str,
        detail: str = "",
        count: int = None,
    ) -> str:
        """Buat SSE string untuk dikirim langsung ke client."""
        payload = {
            "type": "process",
            **self.make(action, detail, count),
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    def to_sentinel(
        self,
        action: str,
        detail: str = "",
        count: int = None,
    ) -> str:
        """
        Buat string sentinel yang bisa lewat chunk stream.
        Format: \x00PROC\x00{json_payload}
        Orchestrator mendeteksi prefix ini dan mengubahnya menjadi OrchestratorEvent.proc().
        """
        payload = self.make(action, detail, count)
        return PROCESS_EVENT_PREFIX + json.dumps(payload, ensure_ascii=False)


# Singleton
process_emitter = ProcessEmitter()
