import os
import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from pydantic import BaseModel
from sqlmodel import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from db.models import KnowledgeDoc, User
from core.auth import get_current_user
from core.config import settings
from rag.engine import rag_engine
from datetime import datetime

router = APIRouter()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Form("default"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload and index a document"""
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(400, f"File type .{ext} not allowed")

    # Check file size
    content = await file.read()
    size_kb = len(content) // 1024
    if size_kb > settings.MAX_UPLOAD_SIZE_MB * 1024:
        raise HTTPException(400, "File too large")

    # Save to disk
    upload_dir = Path(settings.UPLOAD_DIR) / user.id
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = upload_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = KnowledgeDoc(
        user_id=user.id,
        filename=str(file_path),
        original_name=file.filename,
        doc_type=ext,
        file_size_kb=size_kb,
        collection=collection,
        status="indexing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Index async (background)
    import asyncio
    asyncio.create_task(_index_doc(doc.id, str(file_path), {
        "doc_id": doc.id,
        "user_id": user.id,
        "original_name": file.filename,
        "collection": collection,
    }))

    return {"doc_id": doc.id, "filename": file.filename, "status": "indexing"}


async def _index_doc(doc_id: str, file_path: str, metadata: dict):
    from db.database import AsyncSessionLocal
    from db.models import KnowledgeDoc
    result = await rag_engine.index_file(file_path, metadata)
    async with AsyncSessionLocal() as db:
        doc = await db.get(KnowledgeDoc, doc_id)
        if doc:
            doc.status = result["status"]
            doc.chunks = result.get("chunks", 0)
            doc.indexed_at = datetime.utcnow()
            db.add(doc)
            await db.commit()


@router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(KnowledgeDoc)
        .where(KnowledgeDoc.user_id == user.id)
        .order_by(desc(KnowledgeDoc.created_at))
    )
    return result.scalars().all()


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = await db.get(KnowledgeDoc, doc_id)
    if not doc or doc.user_id != user.id:
        raise HTTPException(404, "Document not found")
    await rag_engine.delete_collection(doc_id)
    if Path(doc.filename).exists():
        os.remove(doc.filename)
    await db.delete(doc)
    await db.commit()
    return {"status": "deleted"}


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/query")
async def query_rag(
    req: QueryRequest,
    user: User = Depends(get_current_user),
):
    results = await rag_engine.query(req.query, top_k=req.top_k, user_id=user.id)
    return {"results": results, "count": len(results)}


class ScrapeRequest(BaseModel):
    url: str
    collection: str = "default"


@router.post("/scrape")
async def scrape_website(
    req: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    doc = KnowledgeDoc(
        user_id=user.id,
        filename=req.url,
        original_name=req.url,
        doc_type="web",
        collection=req.collection,
        status="indexing",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    result = await rag_engine.scrape_website(req.url, {
        "doc_id": doc.id,
        "user_id": user.id,
        "original_name": req.url,
    })

    async with (await get_db().__anext__()) as save_db:
        d = await save_db.get(KnowledgeDoc, doc.id)
        if d:
            d.status = result["status"]
            d.chunks = result.get("chunks", 0)
            d.indexed_at = datetime.utcnow()
            save_db.add(d)
            await save_db.commit()

    return result
