import asyncio
from workflow.celery_app import celery_app
import structlog

log = structlog.get_logger()


@celery_app.task
def cleanup_dlq_tasks(retention_days: int = 14):
    """
    Clean up tasks in Dead Letter Queue (DLQ) older than retention_days.
    Fix Point #2: SLA Retensi DLQ ditetapkan 14 hari.
    """
    from db.database import SessionLocal
    from db.models import TaskExecution
    from datetime import datetime, timedelta
    from sqlmodel import select, delete
    
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    log.info("Cleaning up old DLQ tasks", cutoff=cutoff)
    
    with SessionLocal() as db:
        try:
            # SQLModel/SQLAlchemy delete statement
            from sqlalchemy import text
            # Use raw SQL for simplicity across dialects if needed, or stick to delete()
            statement = delete(TaskExecution).where(
                TaskExecution.status == "dlq",
                TaskExecution.created_at < cutoff
            )
            result = db.execute(statement)
            db.commit()
            log.info("DLQ cleanup finished", deleted_count=result.rowcount)
        except Exception as e:
            log.error("DLQ cleanup failed", error=str(e))


@celery_app.task
def check_scheduled_workflows():
    """Check and trigger scheduled tasks that are due.
    Reads ScheduledTask entries with status='pending' and due_at <= now,
    dispatches them as background orchestration tasks, and updates their status.
    """
    from datetime import datetime, timezone
    from db.database import SessionLocal
    from db.models import ScheduledTask
    from sqlmodel import select

    now = datetime.utcnow()
    triggered_count = 0

    try:
        with SessionLocal() as db:
            statement = select(ScheduledTask).where(
                ScheduledTask.status == "pending",
                ScheduledTask.due_at <= now,
            )
            due_tasks = db.exec(statement).all()

            for task in due_tasks:
                try:
                    # Mark as triggered immediately to avoid double-fire
                    task.status = "triggered"
                    task.triggered_at = datetime.utcnow()
                    db.add(task)
                    db.commit()

                    # Dispatch the description as an async orchestration run
                    run_scheduled_task_async.delay(
                        task_id=task.id,
                        session_id=task.session_id,
                        user_id=task.user_id,
                        description=task.description,
                        recurrence=task.recurrence,
                    )
                    triggered_count += 1
                    log.info("Triggered scheduled task", task_id=task.id, title=task.title)
                except Exception as e:
                    log.error("Failed to trigger scheduled task", task_id=task.id, error=str(e))

    except Exception as e:
        log.error("check_scheduled_workflows failed", error=str(e))

    return {"status": "checked", "triggered": triggered_count}



@celery_app.task
def run_scheduled_task_async(task_id: str, session_id: str, user_id: str,
                              description: str, recurrence: str = None):
    """Execute a single scheduled task by running it through the orchestrator.
    Called by check_scheduled_workflows when a due task is found.
    Updates task status to 'done' or 'failed' after completion.
    If task has recurrence, reschedules the next occurrence.
    """
    from datetime import datetime, timezone, timedelta
    from db.database import SessionLocal
    from db.models import ScheduledTask
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result_text = ""

    try:
        # Run the description through a lightweight agent executor
        from core.orchestrator import orchestrator
        events = []
        async def _collect():
            async for event in orchestrator.process(
                message=description,
                session_id=session_id,
                user_id=user_id,
            ):
                if event.type == "chunk":
                    events.append(event.content)
        loop.run_until_complete(_collect())
        result_text = "".join(events)
        log.info("Scheduled task executed", task_id=task_id, result_len=len(result_text))
    except Exception as e:
        result_text = f"Error: {str(e)}"
        log.error("Scheduled task execution failed", task_id=task_id, error=str(e))
    finally:
        loop.close()

    # Update status in DB
    try:
        with SessionLocal() as db:
            from sqlmodel import select
            task = db.exec(select(ScheduledTask).where(ScheduledTask.id == task_id)).first()
            if task:
                task.status = "done" if not result_text.startswith("Error:") else "failed"
                task.result = result_text[:2000]

                # Handle recurrence — reschedule if needed
                if recurrence and task.status == "done":
                    now = datetime.utcnow()
                    if recurrence == "daily":
                        next_due = now + timedelta(days=1)
                    elif recurrence == "weekly":
                        next_due = now + timedelta(weeks=1)
                    else:
                        # Treat as minutes offset fallback
                        next_due = now + timedelta(hours=24)

                    new_task = ScheduledTask(
                        session_id=task.session_id,
                        user_id=task.user_id,
                        title=task.title,
                        description=task.description,
                        due_at=next_due,
                        recurrence=task.recurrence,
                        status="pending",
                    )
                    db.add(new_task)
                    log.info("Rescheduled recurring task", original_id=task_id, next_due=next_due)

                db.add(task)
                db.commit()
    except Exception as e:
        log.error("Failed to update scheduled task status", task_id=task_id, error=str(e))

    return {"task_id": task_id, "status": "done", "result_len": len(result_text)}


@celery_app.task
def run_workflow_task(workflow_id: str, trigger_data: dict):
    """Execute a workflow in the background"""
    log.info("Running workflow", workflow_id=workflow_id)
    return {"workflow_id": workflow_id, "status": "completed"}


@celery_app.task
def send_telegram_message(chat_id: int, text: str):
    """Send message via Telegram"""
    import httpx
    from core.config import settings
    if not settings.TELEGRAM_BOT_TOKEN:
        return {"error": "Telegram not configured"}
    try:
        resp = httpx.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4096]},
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


@celery_app.task
def index_document_task(file_path: str, doc_id: str, metadata: dict):
    """Index a document in the background"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        from rag.engine import rag_engine
        result = loop.run_until_complete(rag_engine.index_file(file_path, metadata))
        return result
    finally:
        loop.close()


@celery_app.task(name="workflow.tasks.save_build_checkpoint")
def save_build_checkpoint(task_id: str, step: str, partial_output: str,
                           completed_steps: list = None, metadata: dict = None):
    """Celery task: persist build checkpoint to DB (fire-and-forget)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        from core.build_checkpoint import build_checkpoint
        return loop.run_until_complete(
            build_checkpoint.save_state(task_id, step, partial_output, completed_steps, metadata)
        )
    finally:
        loop.close()
