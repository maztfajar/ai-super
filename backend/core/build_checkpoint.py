"""
BuildCheckpoint — Persistent build state with Celery task queue integration.
Setiap step build di-commit ke DB sebelum lanjut ke step berikutnya.
"""
import json
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
import structlog

log = structlog.get_logger()


class BuildCheckpoint:
    """Save/resume build state via DB (ExecutionCheckpoint model)."""

    async def save_state(
        self,
        task_id: str,
        step: str,
        partial_output: str,
        completed_steps: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Commit current step progress to DB. Call after each successful step."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ExecutionCheckpoint
            from sqlmodel import select

            data = {
                "task_id": task_id,
                "current_step": step,
                "partial_output": partial_output[:5000],
                "completed_steps": completed_steps or [],
                "metadata": metadata or {},
                "saved_at": datetime.utcnow().isoformat(),
            }

            async with AsyncSessionLocal() as db:
                stmt = select(ExecutionCheckpoint).where(ExecutionCheckpoint.task_id == task_id)
                result = await db.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.checkpoint_data_json = json.dumps(data, ensure_ascii=False)
                    db.add(existing)
                else:
                    db.add(ExecutionCheckpoint(
                        task_id=task_id,
                        checkpoint_data_json=json.dumps(data, ensure_ascii=False),
                    ))
                await db.commit()
            log.info("Checkpoint saved", task_id=task_id, step=step)
            return True
        except Exception as e:
            log.warning("Failed to save checkpoint", task_id=task_id, error=str(e)[:100])
            return False

    async def resume_from(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load last checkpoint for task_id. Returns None if not found."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ExecutionCheckpoint
            from sqlmodel import select

            async with AsyncSessionLocal() as db:
                stmt = select(ExecutionCheckpoint).where(ExecutionCheckpoint.task_id == task_id)
                result = await db.execute(stmt)
                cp = result.scalar_one_or_none()
                if not cp:
                    return None
                data = json.loads(cp.checkpoint_data_json)
                log.info("Resuming from checkpoint", task_id=task_id,
                         step=data.get("current_step"),
                         completed=len(data.get("completed_steps", [])))
                return data
        except Exception as e:
            log.warning("Failed to load checkpoint", task_id=task_id, error=str(e)[:100])
            return None

    async def clear(self, task_id: str) -> None:
        """Delete checkpoint after task completes successfully."""
        try:
            from db.database import AsyncSessionLocal
            from db.models import ExecutionCheckpoint
            from sqlalchemy import delete

            async with AsyncSessionLocal() as db:
                await db.execute(delete(ExecutionCheckpoint).where(
                    ExecutionCheckpoint.task_id == task_id
                ))
                await db.commit()
        except Exception as e:
            log.warning("Failed to clear checkpoint", task_id=task_id, error=str(e)[:80])

    def build_resume_prompt(self, checkpoint: Dict[str, Any]) -> str:
        """Build a system prompt injection to resume from checkpoint."""
        completed = checkpoint.get("completed_steps", [])
        current = checkpoint.get("current_step", "unknown")
        partial = checkpoint.get("partial_output", "")
        lines = [
            "\n[RESUME MODE — LANJUTKAN DARI CHECKPOINT]",
            f"Step terakhir yang berhasil: {current}",
        ]
        if completed:
            lines.append(f"Step yang sudah selesai: {', '.join(completed)}")
        if partial:
            lines.append(f"Output parsial terakhir:\n{partial[:800]}")
        lines.append("JANGAN ulangi step yang sudah selesai. Lanjutkan dari step berikutnya.")
        return "\n".join(lines)


build_checkpoint = BuildCheckpoint()
