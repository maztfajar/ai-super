"""
agents/tools/workflow.py — Workflow Management Tools
=====================================================
Memungkinkan Agent untuk mengelola status sub-task dalam DAG (Directed Acyclic Graph).
"""

import structlog

log = structlog.get_logger()

async def update_task_status(task_id: str, status: str, result: str = "") -> str:
    """
    Update status dari sebuah sub-task dalam rencana eksekusi (DAG).
    
    Args:
        task_id: ID unik dari task (misal: 't1', 't2')
        status: Status baru ('completed', 'failed')
        result: (Opsional) Ringkasan hasil atau pesan error
    """
    # Catatan: Eksekusi sebenarnya diintersepsi oleh AgentExecutor 
    # untuk mengupdate internal DAGManager. 
    # Fungsi ini hanya mengembalikan konfirmasi agar AI tahu permintaannya diterima.
    
    if status not in ("completed", "failed"):
        return f"Error: Status '{status}' tidak valid. Gunakan 'completed' atau 'failed'."
        
    log.info("Task status update requested", task_id=task_id, status=status)
    return f"Status task '{task_id}' berhasil diupdate ke '{status}'."
