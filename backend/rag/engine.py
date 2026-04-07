"""
RAG Engine — Document indexing + semantic search
Dengan integrasi Sumopod Embeddings dan multi-format document processor.
"""
import asyncio
import os
from pathlib import Path
from typing import Optional, List
import structlog

from core.config import settings
from rag.folder_manager import folder_manager

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
        """Initialize RAG engine saat aplikasi startup."""
        # Pastikan semua folder tersedia
        folder_manager.ensure_all_dirs()

        if not _check_rag():
            log.warning(
                "RAG tidak aktif — chromadb/langchain belum terinstall. "
                "Jalankan: pip install -r requirements-full.txt"
            )
            return
        try:
            await asyncio.get_event_loop().run_in_executor(None, self._init_sync)
            self._ready = True
            log.info(
                "RAG engine initialized",
                embedding_provider=settings.EMBEDDING_PROVIDER,
                chroma_dir=settings.CHROMA_PERSIST_DIR,
            )
        except Exception as e:
            log.warning("RAG engine startup gagal (opsional)", error=str(e))

    def _init_sync(self):
        """Inisialisasi embedding dan vectorstore secara sinkron."""
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

        self.embeddings = self._init_embeddings()

        Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)

        try:
            from langchain_community.vectorstores import Chroma
            self.vectorstore = Chroma(
                persist_directory=settings.CHROMA_PERSIST_DIR,
                embedding_function=self.embeddings,
                collection_name="ai-super-assistant",
            )
        except Exception as e:
            log.error("Gagal init Chroma vectorstore", error=str(e))
            raise

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=64,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        log.info("Vector store dan text splitter siap")

    def _init_embeddings(self):
        """
        Inisialisasi embedding model berdasarkan EMBEDDING_PROVIDER.
        Priority: sumopod → openai → google → local → fake
        """
        provider = settings.EMBEDDING_PROVIDER.lower()
        log.info("Inisialisasi embedding", provider=provider)

        # ── SUMOPOD ──────────────────────────────────────────────
        if provider == "sumopod" and settings.SUMOPOD_API_KEY:
            try:
                from rag.embedding_service import SumopodEmbeddings
                embeddings = SumopodEmbeddings(
                    api_key=settings.SUMOPOD_API_KEY,
                    base_url=settings.SUMOPOD_HOST,
                    model=settings.SUMOPOD_EMBEDDING_MODEL,
                )
                # Quick connection test
                result = embeddings.test_connection()
                if result["status"] == "ok":
                    log.info(
                        "Sumopod Embeddings aktif",
                        model=result["model"],
                        dim=result["embedding_dim"],
                        latency=result["latency_seconds"],
                    )
                    return embeddings
                else:
                    log.warning("Sumopod connection test gagal, coba provider lain", error=result.get("error"))
            except Exception as e:
                log.error("Gagal init Sumopod embeddings", error=str(e))

        # ── OPENAI ───────────────────────────────────────────────
        if provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from langchain_openai import OpenAIEmbeddings
                embeddings = OpenAIEmbeddings(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    openai_api_key=settings.OPENAI_API_KEY,
                )
                log.info("OpenAI Embeddings aktif", model=settings.OPENAI_EMBEDDING_MODEL)
                return embeddings
            except Exception as e:
                log.error("Gagal init OpenAI embeddings", error=str(e))

        # ── GOOGLE ───────────────────────────────────────────────
        if provider == "google" and settings.GOOGLE_API_KEY:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=settings.GOOGLE_API_KEY,
                )
                log.info("Google Gemini Embeddings aktif")
                return embeddings
            except Exception as e:
                log.error("Gagal init Google embeddings", error=str(e))

        # ── OPENAI via Sumopod (fallback jika provider=openai tapi key Sumopod ada) ──
        if settings.SUMOPOD_API_KEY and provider not in ("sumopod",):
            try:
                from rag.embedding_service import SumopodEmbeddings
                embeddings = SumopodEmbeddings(
                    api_key=settings.SUMOPOD_API_KEY,
                    base_url=settings.SUMOPOD_HOST,
                    model=settings.SUMOPOD_EMBEDDING_MODEL,
                )
                result = embeddings.test_connection()
                if result["status"] == "ok":
                    log.info(
                        "Sumopod Embeddings aktif (fallback)",
                        model=result["model"],
                        dim=result["embedding_dim"],
                    )
                    return embeddings
            except Exception as e:
                log.warning("Sumopod fallback juga gagal", error=str(e))

        # ── LOCAL HuggingFace ─────────────────────────────────────
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
            log.info("HuggingFace local embeddings aktif", model=settings.EMBEDDING_MODEL)
            return embeddings
        except Exception:
            pass

        # ── FAKE (last resort) ────────────────────────────────────
        try:
            from langchain_community.embeddings import FakeEmbeddings
            log.warning("Pakai FakeEmbeddings — install sentence-transformers untuk RAG nyata")
            return FakeEmbeddings(size=384)
        except Exception as e2:
            raise RuntimeError(f"Tidak bisa init embeddings apapun: {e2}")

    # ── Document Indexing ─────────────────────────────────────────

    async def index_file(self, file_path: str, metadata: dict) -> dict:
        """
        Index satu file ke vectorstore.
        Gunakan DocumentProcessor untuk parsing multi-format.
        """
        if not self._ready:
            return {
                "status": "skipped",
                "message": "RAG belum aktif. Install: pip install -r requirements-full.txt",
                "chunks": 0,
            }

        p = Path(file_path)
        if not p.exists():
            return {"status": "error", "message": f"File tidak ditemukan: {file_path}", "chunks": 0}

        if p.stat().st_size == 0:
            return {"status": "error", "message": "File kosong (0 bytes)", "chunks": 0}

        try:
            # Coba pakai DocumentProcessor baru (multi-format)
            try:
                from rag.document_processor import document_processor
                chunks = await document_processor.extract_async(
                    file_path, extra_metadata=metadata, timeout=45
                )
                if chunks:
                    # Convert ProcessedChunk ke LangChain Document format for Chroma
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._add_processed_chunks, chunks
                    )
                    log.info("File berhasil diindex via DocumentProcessor", file=p.name, chunks=len(chunks))
                    return {"status": "indexed", "chunks": len(chunks)}
            except ImportError:
                pass  # Fallback ke metode lama

            # Fallback: LangChain loaders
            docs = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, self._load_and_split, file_path, metadata
                ),
                timeout=45,
            )
            if not docs:
                return {"status": "error", "message": "Tidak ada konten berhasil diekstrak", "chunks": 0}

            await asyncio.get_event_loop().run_in_executor(None, self._add_to_store, docs)
            return {"status": "indexed", "chunks": len(docs)}

        except asyncio.TimeoutError:
            log.error("Index file timeout (45s)", file=file_path)
            return {"status": "error", "message": "Timeout saat memproses dokumen (>45 detik)", "chunks": 0}
        except Exception as e:
            log.error("Index gagal", file=file_path, error=str(e))
            return {"status": "error", "message": str(e), "chunks": 0}

    def _add_processed_chunks(self, chunks):
        """Tambahkan ProcessedChunk ke vectorstore."""
        from langchain_core.documents import Document
        lc_docs = [
            Document(page_content=chunk.page_content, metadata=chunk.metadata)
            for chunk in chunks
        ]
        
        # Split documents to ensure they fit context window before adding to ChromaDB
        if self.text_splitter:
            split_docs = self.text_splitter.split_documents(lc_docs)
            self.vectorstore.add_documents(split_docs)
        else:
            self.vectorstore.add_documents(lc_docs)

    def _load_and_split(self, file_path: str, metadata: dict) -> list:
        """Fallback: LangChain community loaders."""
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
            raise ValueError(f"Tipe file tidak didukung via fallback: {ext}")

        docs = loader.load()
        if not docs:
            log.warning("Tidak ada konten dari file", file_path=file_path)
            return []

        chunks = self.text_splitter.split_documents(docs)
        for chunk in chunks:
            chunk.metadata.update(metadata)
        return chunks

    def _add_to_store(self, docs: list):
        """Tambahkan LangChain documents ke vectorstore."""
        self.vectorstore.add_documents(docs)

    # ── Batch Indexing dari folder rag_documents ──────────────────

    async def index_rag_documents_folder(self, user_id: str, collection: str = "default") -> dict:
        """
        Scan dan index semua file di folder /rag_documents.
        Berguna untuk bulk import dokumen.
        """
        if not self._ready:
            return {"status": "error", "message": "RAG belum aktif", "indexed": 0, "failed": 0}

        scan = folder_manager.check_rag_documents()
        files = [f for f in scan["files"] if not f["is_empty"]]

        if not files:
            return {
                "status": "ok",
                "message": f"Tidak ada file di {scan['directory']}",
                "indexed": 0,
                "failed": 0,
                "directory": scan["directory"],
            }

        indexed = 0
        failed = 0
        errors = []

        for file_info in files:
            file_path = file_info["path"]
            metadata = {
                "user_id": user_id,
                "original_name": file_info["name"],
                "collection": collection,
                "source": "rag_documents_folder",
            }
            try:
                result = await self.index_file(file_path, metadata)
                if result["status"] == "indexed":
                    indexed += 1
                    log.info("File terindex", name=file_info["name"], chunks=result["chunks"])
                else:
                    failed += 1
                    errors.append(f"{file_info['name']}: {result.get('message', 'unknown error')}")
                    log.warning("File gagal diindex", name=file_info["name"], error=result.get("message"))
            except Exception as e:
                failed += 1
                errors.append(f"{file_info['name']}: {str(e)}")
                log.error("Exception saat index file", name=file_info["name"], error=str(e))

        return {
            "status": "ok",
            "indexed": indexed,
            "failed": failed,
            "total": len(files),
            "errors": errors,
            "directory": scan["directory"],
        }

    # ── Query ─────────────────────────────────────────────────────

    async def query(self, question: str, top_k: int = 5, user_id: Optional[str] = None) -> List[dict]:
        """Semantic search di vectorstore."""
        if not self._ready:
            return []
        try:
            results = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.vectorstore.similarity_search_with_score(question, k=top_k),
                ),
                timeout=30,
            )
            return [
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("original_name", doc.metadata.get("filename", "unknown")),
                    "score": float(score),
                    "metadata": doc.metadata,
                }
                for doc, score in results
            ]
        except asyncio.TimeoutError:
            log.error("RAG query timeout (30s)", question=question[:100])
            return []
        except Exception as e:
            log.error("RAG query gagal", error=str(e))
            return []

    def build_context(self, rag_results: list) -> str:
        """Format RAG results menjadi context string untuk LLM."""
        if not rag_results:
            return ""
        ctx = "### Dokumen relevan dari knowledge base kamu:\n\n"
        for i, r in enumerate(rag_results[:3], 1):
            ctx += f"**Sumber {i}: {r['source']}**\n{r['content']}\n\n"
        return ctx

    # ── Web Scraping ──────────────────────────────────────────────

    async def scrape_website(self, url: str, metadata: dict) -> dict:
        """Scrape dan index website."""
        if not self._ready:
            return {"status": "skipped", "message": "RAG belum aktif", "chunks": 0}
        try:
            from langchain_community.document_loaders import WebBaseLoader
            docs = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: WebBaseLoader([url]).load()
                ),
                timeout=30,
            )
            chunks = self.text_splitter.split_documents(docs)
            for chunk in chunks:
                chunk.metadata.update(metadata)
            await asyncio.get_event_loop().run_in_executor(None, self._add_to_store, chunks)
            return {"status": "indexed", "url": url, "chunks": len(chunks)}
        except asyncio.TimeoutError:
            return {"status": "error", "message": "Website scraping timeout (30s)"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ── Delete ────────────────────────────────────────────────────

    async def delete_collection(self, doc_id: str):
        """Hapus dokumen dari vectorstore berdasarkan doc_id."""
        if self._ready and self.vectorstore:
            try:
                self.vectorstore._collection.delete(where={"doc_id": doc_id})
            except Exception:
                pass

    # ── Status ───────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Return status RAG engine."""
        provider = settings.EMBEDDING_PROVIDER
        embedding_model = "unknown"
        if self.embeddings:
            try:
                embedding_model = getattr(self.embeddings, "model", None) or \
                                  getattr(self.embeddings, "model_name", None) or \
                                  type(self.embeddings).__name__
            except Exception:
                pass

        doc_count = 0
        if self._ready and self.vectorstore:
            try:
                doc_count = self.vectorstore._collection.count()
            except Exception:
                pass

        folder_status = folder_manager.get_status()
        rag_docs_scan = folder_manager.check_rag_documents() if self._ready else {}

        return {
            "ready": self._ready,
            "embedding_provider": provider,
            "embedding_model": embedding_model,
            "chroma_dir": settings.CHROMA_PERSIST_DIR,
            "total_chunks": doc_count,
            "folders": folder_status,
            "rag_documents": {
                "total_files": rag_docs_scan.get("total_files", 0),
                "directory": rag_docs_scan.get("directory", ""),
            },
        }

    @property
    def is_ready(self) -> bool:
        return self._ready


rag_engine = RAGEngine()
