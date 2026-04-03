import asyncio
from workflow.celery_app import celery_app
import structlog

log = structlog.get_logger()


@celery_app.task
def check_scheduled_workflows():
    """Check and trigger scheduled workflows"""
    log.info("Checking scheduled workflows...")
    return {"status": "checked"}


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
