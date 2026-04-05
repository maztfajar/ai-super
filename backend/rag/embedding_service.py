"""
Sumopod Embedding Service
Custom LangChain-compatible embeddings menggunakan Sumopod API.
Endpoint: {SUMOPOD_HOST}/embeddings
Model: text-embedding-3-small (compatible OpenAI format)
"""
import time
import logging
from typing import List, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import structlog

log = structlog.get_logger()

# LangChain base class
try:
    from langchain_core.embeddings import Embeddings
except ImportError:
    try:
        from langchain.embeddings.base import Embeddings
    except ImportError:
        # Fallback minimal protocol
        class Embeddings:
            def embed_documents(self, texts: List[str]) -> List[List[float]]: ...
            def embed_query(self, text: str) -> List[float]: ...


class SumopodEmbeddings(Embeddings):
    """
    LangChain-compatible embedding menggunakan Sumopod API.
    Sumopod menggunakan format OpenAI-compatible /v1/embeddings.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://ai.sumopod.com/v1",
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.timeout = timeout
        self._session = self._create_session()

        log.info(
            "SumopodEmbeddings initialized",
            base_url=self.base_url,
            model=self.model,
            batch_size=self.batch_size,
        )

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        retry = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a single batch of texts (max batch_size)."""
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }

        try:
            response = self._session.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # OpenAI-compatible response format
            embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
            log.debug(
                "Sumopod batch embedded",
                count=len(texts),
                dim=len(embeddings[0]) if embeddings else 0,
            )
            return embeddings

        except requests.exceptions.Timeout:
            log.error("Sumopod embedding timeout", url=url, count=len(texts))
            raise TimeoutError(f"Sumopod embedding request timed out after {self.timeout}s")
        except requests.exceptions.HTTPError as e:
            log.error(
                "Sumopod embedding HTTP error",
                status=e.response.status_code if e.response else "?",
                body=e.response.text[:500] if e.response else "",
            )
            raise
        except Exception as e:
            log.error("Sumopod embedding failed", error=str(e))
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of documents.
        Automatically batched if len(texts) > batch_size.
        """
        if not texts:
            return []

        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            log.debug("Embedding batch", start=i, end=i + len(batch), total=len(texts))

            for attempt in range(self.max_retries):
                try:
                    embeddings = self._embed_batch(batch)
                    all_embeddings.extend(embeddings)
                    break
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        wait = 2 ** attempt
                        log.warning(
                            f"Sumopod batch embed attempt {attempt+1} gagal, retry dalam {wait}s",
                            error=str(e),
                        )
                        time.sleep(wait)
                    else:
                        log.error("Semua retry gagal untuk batch embedding", error=str(e))
                        raise

        return all_embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        results = self.embed_documents([text])
        return results[0] if results else []

    def test_connection(self) -> dict:
        """Test koneksi ke Sumopod API. Return dict dengan status."""
        try:
            start = time.time()
            test_embedding = self.embed_query("test koneksi Sumopod")
            elapsed = round(time.time() - start, 3)

            return {
                "status": "ok",
                "model": self.model,
                "base_url": self.base_url,
                "embedding_dim": len(test_embedding),
                "latency_seconds": elapsed,
            }
        except Exception as e:
            return {
                "status": "error",
                "model": self.model,
                "base_url": self.base_url,
                "error": str(e),
            }


def get_sumopod_embeddings(
    api_key: str,
    base_url: str = "https://ai.sumopod.com/v1",
    model: str = "text-embedding-3-small",
) -> SumopodEmbeddings:
    """Factory function untuk membuat SumopodEmbeddings instance."""
    return SumopodEmbeddings(api_key=api_key, base_url=base_url, model=model)
