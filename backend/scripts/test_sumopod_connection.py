#!/usr/bin/env python3
"""
Test koneksi ke Sumopod Embedding API.
Jalankan: python scripts/test_sumopod_connection.py
"""
import sys
import os
import time

# Tambahkan path backend ke sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load .env dari root project
env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(env_path)


def banner(text: str):
    print("\n" + "═" * 55)
    print(f"  {text}")
    print("═" * 55)


def ok(msg): print(f"  ✅ {msg}")
def err(msg): print(f"  ❌ {msg}")
def info(msg): print(f"  ℹ️  {msg}")
def warn(msg): print(f"  ⚠️  {msg}")


def test_env():
    banner("1. Cek Environment Variables")
    api_key = os.environ.get("SUMOPOD_API_KEY", "")
    host = os.environ.get("SUMOPOD_HOST", "https://ai.sumopod.com/v1")
    embedding_model = os.environ.get("SUMOPOD_EMBEDDING_MODEL", "text-embedding-3-small")

    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:]
        ok(f"SUMOPOD_API_KEY ditemukan: {masked}")
    else:
        err("SUMOPOD_API_KEY tidak ada di .env!")
        return None, None, None

    ok(f"SUMOPOD_HOST: {host}")
    ok(f"SUMOPOD_EMBEDDING_MODEL: {embedding_model}")
    return api_key, host, embedding_model


def test_connection(api_key, host, model):
    banner("2. Test Koneksi HTTP ke Sumopod")
    import requests

    url = f"{host.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": ["Halo, ini adalah test embedding dari Pitakonku AI."],
    }

    try:
        start = time.time()
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        elapsed = round(time.time() - start, 3)

        if resp.status_code == 200:
            data = resp.json()
            embedding = data["data"][0]["embedding"]
            ok(f"Koneksi berhasil! Status: {resp.status_code}")
            ok(f"Embedding dimensi: {len(embedding)}")
            ok(f"Latency: {elapsed}s")
            ok(f"Model yang digunakan: {data.get('model', model)}")
            if "usage" in data:
                info(f"Token terpakai: {data['usage']}")
            return True, embedding
        else:
            err(f"HTTP Error {resp.status_code}")
            try:
                err(f"Response: {resp.json()}")
            except Exception:
                err(f"Response body: {resp.text[:300]}")
            return False, None

    except requests.exceptions.Timeout:
        err("Timeout setelah 30 detik — cek koneksi internet/VPS")
        return False, None
    except requests.exceptions.ConnectionError as e:
        err(f"Tidak bisa konek ke {url}")
        err(f"Detail: {e}")
        return False, None
    except Exception as e:
        err(f"Error tidak dikenal: {e}")
        return False, None


def test_sumopod_embeddings_class(api_key, host, model):
    banner("3. Test SumopodEmbeddings Class (LangChain)")
    try:
        from rag.embedding_service import SumopodEmbeddings

        embedder = SumopodEmbeddings(api_key=api_key, base_url=host, model=model)

        # Test single query
        start = time.time()
        vec = embedder.embed_query("NIK Meryet adalah 3301010101010001")
        elapsed = round(time.time() - start, 3)

        ok(f"embed_query() berhasil: dim={len(vec)}, latency={elapsed}s")

        # Test batch
        start = time.time()
        texts = [
            "Data kependudukan Desa Pengasih",
            "NIK: 3301010101010001, Nama: Meryet",
            "Tanggal lahir 01 Januari 1980",
        ]
        vecs = embedder.embed_documents(texts)
        elapsed = round(time.time() - start, 3)
        ok(f"embed_documents() berhasil: {len(vecs)} vectors, latency={elapsed}s")

        # Test similarity (cosine)
        import math
        def cosine(a, b):
            dot = sum(x*y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x**2 for x in a))
            norm_b = math.sqrt(sum(x**2 for x in b))
            return dot / (norm_a * norm_b + 1e-10)

        sim_1_2 = round(cosine(vecs[0], vecs[1]), 4)
        sim_1_3 = round(cosine(vecs[0], vecs[2]), 4)
        info(f"Similarity 'Desa' vs 'NIK+Nama': {sim_1_2}")
        info(f"Similarity 'Desa' vs 'Tanggal lahir': {sim_1_3}")

        return True

    except ImportError as e:
        err(f"Gagal import SumopodEmbeddings: {e}")
        return False
    except Exception as e:
        err(f"Test SumopodEmbeddings gagal: {e}")
        return False


def test_chromadb():
    banner("4. Test ChromaDB")
    try:
        import chromadb
        ok(f"chromadb terinstall: v{chromadb.__version__}")
        return True
    except ImportError:
        warn("chromadb belum terinstall")
        warn("Jalankan: pip install chromadb>=0.5.0")
        return False


def test_document_processor():
    banner("5. Test Document Processor")
    try:
        from rag.document_processor import DocumentProcessor
        dp = DocumentProcessor()
        supported = ", ".join(sorted(dp.SUPPORTED_EXTENSIONS))
        ok(f"DocumentProcessor OK, format didukung: {supported}")
        return True
    except Exception as e:
        err(f"Document Processor gagal: {e}")
        return False


def test_folders():
    banner("6. Test Folder Manager")
    try:
        from rag.folder_manager import folder_manager
        results = folder_manager.ensure_all_dirs()
        for path, status in results.items():
            if status == "OK":
                ok(f"{status}: {path}")
            else:
                err(f"{status}: {path}")

        scan = folder_manager.check_rag_documents()
        info(f"Folder rag_documents: {scan['directory']}")
        info(f"File ditemukan: {scan['total_files']}")
        if scan["empty_files"]:
            warn(f"File kosong (skip): {scan['empty_files']}")
        return True
    except Exception as e:
        err(f"Folder manager gagal: {e}")
        return False


def main():
    print("\n" + "█" * 55)
    print("  PITAKONKU — Test Sumopod RAG Connection")
    print("█" * 55)

    # 1. Check env
    api_key, host, model = test_env()
    if not api_key:
        print("\n❌ Test berhenti: SUMOPOD_API_KEY tidak ditemukan di .env")
        sys.exit(1)

    # 2. HTTP test
    connected, embedding = test_connection(api_key, host, model)

    # 3. LangChain class test
    if connected:
        test_sumopod_embeddings_class(api_key, host, model)

    # 4. ChromaDB test
    test_chromadb()

    # 5. Document processor test
    test_document_processor()

    # 6. Folder test
    test_folders()

    # Summary
    banner("RINGKASAN")
    if connected:
        ok("Sumopod API: AKTIF ✓")
        ok("Sistem RAG siap digunakan!")
        print()
        print("  Langkah selanjutnya:")
        print("  1. Set EMBEDDING_PROVIDER=sumopod di .env")
        print("  2. Restart server: sudo systemctl restart pitakonku")
        print("  3. Upload dokumen lewat UI → Knowledge > Upload")
        print("  4. Atau taruh file di /rag_documents/ lalu scan lewat UI")
    else:
        err("Sumopod API: TIDAK AKTIF")
        print()
        print("  Troubleshooting:")
        print("  1. Cek SUMOPOD_API_KEY di .env")
        print("  2. Cek SUMOPOD_HOST di .env (default: https://ai.sumopod.com/v1)")
        print("  3. Pastikan server Sumopod dapat diakses dari VPS ini")
        print("  4. Cek apakah model text-embedding-3-small tersedia di Sumopod")
    print()


if __name__ == "__main__":
    main()
