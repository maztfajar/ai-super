import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import AsyncSessionLocal
from db.models import KnowledgeDoc
from rag.engine import rag_engine
from sqlmodel import select

async def main():
    print("Memulai RAG engine...")
    await rag_engine.startup()
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(KnowledgeDoc).where(KnowledgeDoc.status == "error"))
        docs = result.scalars().all()
        
        if not docs:
            print("Tidak ada dokumen yang error.")
            return

        for doc in docs:
            print(f"\nMemproses {doc.original_name} (ID: {doc.id})...")
            if not os.path.exists(doc.filename):
                print(f"File tidak ada: {doc.filename}")
                continue
                
            res = await rag_engine.index_file(doc.filename, {
                "doc_id": doc.id,
                "user_id": doc.user_id,
                "original_name": doc.original_name,
                "collection": doc.collection
            })
            
            if res["status"] == "indexed":
                doc.status = "ready"
                doc.chunks = res.get("chunks", 0)
                print(f"BERHASIL: {res['chunks']} chunks diindeks.")
            else:
                print(f"GAGAL: {res.get('message')}")
            
            db.add(doc)
            await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
