"""
RAG Engine — Document indexing + semantic search
Install package RAG dulu: pip install -r requirements-full.txt
"""
import asyncio
import os
from pathlib import Path
from typing import Optional, List
import structlog

from core.config import settings

log = structlog.get_logger()

# Flag apakah RAG tersedia
RAG_AVAILABLE = False


def _check_rag():
    global RAG_AVAILABLE
    try:
        import chromadb  # noqa
        RAG_AVAILABLE = True
    except ImportError:
        RAG_AVAILABLE = False
    return RAG_AVAILABLE


class RAGEngine:
    def __init__(self):
        self.vectorstore = None
        self.embeddings = None
        self.text_splitter = None
        self._ready = False

    async def startup(self):
        if not _check_rag():
            log.warning(
                "RAG tidak aktif — chromadb/langchain belum terinstall. "
                "Jalankan: pip install -r requirements-full.txt"
            )
            return
        try:
            await asyncio.get_event_loop().run_in_executor(None, self._init_sync)
            self._ready = True
            log.info("RAG engine initialized")
        except Exception as e:
            log.warning("RAG engine startup gagal (opsional)", error=str(e))

    def _init_sync(self):
        from langchain_community.vectorstores import Chroma
        from langchain.text_splitter import RecursiveCharacterTextSplitter

        # Coba HuggingFace embeddings (lokal)
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except Exception:
            try:
                from langchain_community.embeddings import FakeEmbeddings
                self.embeddings = FakeEmbeddings(size=384)
                log.warning("Pakai FakeEmbeddings — install sentence-transformers untuk RAG nyata")
            except Exception as e2:
                raise RuntimeError(f"Tidak bisa init embeddings: {e2}")

        Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        self.vectorstore = Chroma(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            embedding_function=self.embeddings,
            collection_name="ai-super-assistant",
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512, chunk_overlap=64,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    async def index_file(self, file_path: str, metadata: dict) -> dict:
        if not self._ready:
            return {"status": "skipped", "message": "RAG belum aktif. Install: pip install -r requirements-full.txt", "chunks": 0}
        try:
            docs = await asyncio.get_event_loop().run_in_executor(
                None, self._load_and_split, file_path, metadata
            )
            await asyncio.get_event_loop().run_in_executor(None, self._add_to_store, docs)
            return {"status": "indexed", "chunks": len(docs)}
        except Exception as e:
            log.error("Index gagal", error=str(e))
            return {"status": "error", "message": str(e), "chunks": 0}

    def _load_and_split(self, file_path: str, metadata: dict) -> list:
        path = Path(file_path)
        ext = path.suffix.lower()
        if ext == ".pdf":
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
        elif ext == ".docx":
            from langchain_community.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
        elif ext in [".txt", ".md"]:
            from langchain_community.document_loaders import TextLoader
            loader = TextLoader(file_path, encoding="utf-8")
        elif ext == ".csv":
            from langchain_community.document_loaders.csv_loader import CSVLoader
            loader = CSVLoader(file_path)
        else:
            raise ValueError(f"Tipe file tidak didukung: {ext}")
        docs = loader.load()
        chunks = self.text_splitter.split_documents(docs)
        for chunk in chunks:
            chunk.metadata.update(metadata)
        return chunks

    def _add_to_store(self, docs: list):
        self.vectorstore.add_documents(docs)

    async def query(self, question: str, top_k: int = 5, user_id: Optional[str] = None) -> List[dict]:
        if not self._ready:
            return []
        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.vectorstore.similarity_search_with_score(question, k=top_k),
            )
            return [
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("original_name", "unknown"),
                    "score": float(score),
                }
                for doc, score in results
            ]
        except Exception as e:
            log.error("RAG query gagal", error=str(e))
            return []

    def build_context(self, rag_results: list) -> str:
        if not rag_results:
            return ""
        ctx = "### Dokumen relevan dari knowledge base kamu:\n\n"
        for i, r in enumerate(rag_results[:3], 1):
            ctx += f"**Sumber {i}: {r['source']}**\n{r['content']}\n\n"
        return ctx

    async def scrape_website(self, url: str, metadata: dict) -> dict:
        if not self._ready:
            return {"status": "skipped", "message": "RAG belum aktif", "chunks": 0}
        try:
            from langchain_community.document_loaders import WebBaseLoader
            docs = await asyncio.get_event_loop().run_in_executor(
                None, lambda: WebBaseLoader([url]).load()
            )
            chunks = self.text_splitter.split_documents(docs)
            for chunk in chunks:
                chunk.metadata.update(metadata)
            await asyncio.get_event_loop().run_in_executor(None, self._add_to_store, chunks)
            return {"status": "indexed", "url": url, "chunks": len(chunks)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def delete_collection(self, doc_id: str):
        if self._ready and self.vectorstore:
            try:
                self.vectorstore._collection.delete(where={"doc_id": doc_id})
            except Exception:
                pass

    @property
    def is_ready(self) -> bool:
        return self._ready


rag_engine = RAGEngine()
