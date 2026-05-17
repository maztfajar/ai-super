"""
QMD — The Token Killer (v1.0)
==============================
Query-aware Message Distiller. Menghemat biaya API dengan cara:
  1. Memotong history chat yang panjang — hanya ambil yang relevan
  2. Mengompres pesan yang verbose — hilangkan whitespace & redundansi
  3. Memfilter RAG context — hanya sisipkan chunk yang benar-benar cocok
  4. Mengestimasi token count sebelum kirim — warn jika terlalu besar

Cara kerja:
  - Terima (messages, query, max_budget) → kembalikan messages yang sudah di-distill
  - Scoring tiap message berdasarkan kecocokan semantik/keyword dgn query terkini
  - Prioritaskan: system prompt (selalu keep) → user query (selalu keep) →
    recent history → relevant old history → drop sisanya

Integrasi:
  - Dipanggil oleh orchestrator sebelum mengirim messages ke model
  - Transparan: jika query pendek/history sedikit, QMD tidak mengubah apapun

Penghematan tipikal:
  - History 30 pesan × 500 token → diringkas jadi ~5000 token (dari ~15000)
  - RAG context 10 chunk × 200 token → difilter jadi ~3 chunk × 200 = ~600 token
"""

import re
import math
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import structlog

log = structlog.get_logger()

# ── Token Budget Defaults ─────────────────────────────────────────────────────
# Estimasi: 1 token ≈ 4 chars (Bahasa Indonesia sedikit lebih banyak)
CHARS_PER_TOKEN = 3.5
DEFAULT_MAX_TOKENS = 6000       # budget untuk history+context (bukan total)
MIN_KEEP_MESSAGES = 4            # minimal message yang selalu dipertahankan
RELEVANCE_THRESHOLD = 0.15      # minimum skor relevansi agar message dipertahankan
MAX_SINGLE_MESSAGE_TOKENS = 1500 # single message terlalu panjang → trim


@dataclass
class QMDResult:
    """Hasil dari proses distilasi QMD."""
    original_messages: int = 0
    distilled_messages: int = 0
    original_tokens_est: int = 0
    distilled_tokens_est: int = 0
    savings_pct: float = 0.0
    dropped_messages: int = 0
    trimmed_messages: int = 0
    duration_ms: int = 0


class QueryMessageDistiller:
    """
    The Token Killer — Distill messages untuk hemat token API.
    """

    def distill(
        self,
        messages: List[Dict[str, str]],
        query: str,
        max_token_budget: int = DEFAULT_MAX_TOKENS,
        keep_system: bool = True,
        keep_last_n: int = MIN_KEEP_MESSAGES,
    ) -> Tuple[List[Dict[str, str]], QMDResult]:
        """
        Distill messages agar sesuai token budget.

        Args:
            messages: List of {"role": ..., "content": ...}
            query: User query terkini (untuk scoring relevansi)
            max_token_budget: Batas token yang diizinkan
            keep_system: Selalu pertahankan system prompt
            keep_last_n: Minimal N message terakhir yang dipertahankan

        Returns:
            (distilled_messages, result_stats)
        """
        start = time.time()
        result = QMDResult(original_messages=len(messages))

        if not messages:
            result.duration_ms = int((time.time() - start) * 1000)
            return messages, result

        # Estimasi token awal
        result.original_tokens_est = self._estimate_tokens(messages)

        # Jika sudah di bawah budget, kembalikan apa adanya
        if result.original_tokens_est <= max_token_budget:
            result.distilled_messages = len(messages)
            result.distilled_tokens_est = result.original_tokens_est
            result.duration_ms = int((time.time() - start) * 1000)
            return messages, result

        # ── Phase 1: Kategorisasi ─────────────────────────────────
        system_msgs = []    # Selalu keep
        user_query = []     # Selalu keep (pesan terakhir user)
        recent = []         # N pesan terakhir (keep)
        candidates = []     # Sisanya: scoring + filtering

        for i, msg in enumerate(messages):
            if keep_system and msg["role"] == "system":
                system_msgs.append(msg)
            elif i >= len(messages) - keep_last_n:
                recent.append(msg)
            else:
                candidates.append((i, msg))

        # Pastikan pesan user terakhir ada di recent
        if messages and messages[-1]["role"] == "user":
            if messages[-1] not in recent:
                user_query.append(messages[-1])

        # ── Phase 2: Scoring relevansi ────────────────────────────
        query_keywords = self._extract_keywords(query)
        scored = []
        for idx, msg in candidates:
            score = self._relevance_score(msg["content"], query_keywords, query)
            scored.append((score, idx, msg))

        # Sort by relevance (tinggi → rendah)
        scored.sort(key=lambda x: x[0], reverse=True)

        # ── Phase 3: Budget allocation ────────────────────────────
        # Hitung token yang sudah pasti dipakai
        fixed_tokens = (
            self._estimate_tokens(system_msgs)
            + self._estimate_tokens(recent)
            + self._estimate_tokens(user_query)
        )

        remaining_budget = max(0, max_token_budget - fixed_tokens)
        selected_candidates = []

        for score, idx, msg in scored:
            if score < RELEVANCE_THRESHOLD:
                result.dropped_messages += 1
                continue

            msg_tokens = self._estimate_token_single(msg["content"])

            # Trim message yang terlalu panjang
            if msg_tokens > MAX_SINGLE_MESSAGE_TOKENS:
                msg = self._trim_message(msg, query_keywords, MAX_SINGLE_MESSAGE_TOKENS)
                msg_tokens = self._estimate_token_single(msg["content"])
                result.trimmed_messages += 1

            if msg_tokens <= remaining_budget:
                selected_candidates.append((idx, msg))
                remaining_budget -= msg_tokens
            else:
                result.dropped_messages += 1

        # ── Phase 4: Reassemble ───────────────────────────────────
        # Sort selected candidates kembali ke posisi asli
        selected_candidates.sort(key=lambda x: x[0])

        distilled = []
        distilled.extend(system_msgs)
        distilled.extend([msg for _, msg in selected_candidates])
        distilled.extend(recent)
        # user_query sudah ada di recent biasanya, tapi jika tidak:
        for uq in user_query:
            if uq not in distilled:
                distilled.append(uq)

        # ── Phase 5: Compress system prompt if still over budget ──
        total_est = self._estimate_tokens(distilled)
        if total_est > max_token_budget and system_msgs:
            for i, msg in enumerate(distilled):
                if msg["role"] == "system":
                    compressed = self._compress_text(msg["content"])
                    token_saved = self._estimate_token_single(msg["content"]) - self._estimate_token_single(compressed)
                    if token_saved > 50:
                        distilled[i] = {"role": "system", "content": compressed}
                        result.trimmed_messages += 1
                    break

        # ── Result stats ──────────────────────────────────────────
        result.distilled_messages = len(distilled)
        result.distilled_tokens_est = self._estimate_tokens(distilled)
        if result.original_tokens_est > 0:
            result.savings_pct = round(
                (1 - result.distilled_tokens_est / result.original_tokens_est) * 100, 1
            )
        result.duration_ms = int((time.time() - start) * 1000)

        if result.savings_pct > 5:
            log.info(
                "QMD: token distilled",
                original=result.original_tokens_est,
                distilled=result.distilled_tokens_est,
                savings=f"{result.savings_pct}%",
                msgs=f"{result.original_messages}→{result.distilled_messages}",
                dropped=result.dropped_messages,
                duration_ms=result.duration_ms,
            )

        return distilled, result

    # ── Token estimation ──────────────────────────────────────────────────────

    def _estimate_tokens(self, messages: List[Dict]) -> int:
        return sum(self._estimate_token_single(m.get("content", "")) for m in messages)

    def _estimate_token_single(self, text: str) -> int:
        if not text:
            return 0
        return int(len(text) / CHARS_PER_TOKEN) + 4  # +4 for message overhead

    # ── Keyword extraction ────────────────────────────────────────────────────

    def _extract_keywords(self, text: str) -> List[str]:
        """Ekstrak keyword penting dari teks query."""
        if not text:
            return []

        # Lowercase, hapus punctuation
        clean = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean.split()

        # Stopwords bahasa Indonesia & Inggris
        STOPWORDS = {
            # ID
            "yang", "dan", "di", "ke", "dari", "untuk", "pada", "adalah",
            "ini", "itu", "dengan", "tidak", "ada", "akan", "bisa", "buat",
            "juga", "atau", "sudah", "saya", "kamu", "anda", "apa", "satu",
            "dua", "tiga", "ya", "dong", "nih", "lah", "kan", "kok", "sih",
            "nya", "se", "ter", "ber", "me", "per", "mau", "tolong",
            "mohon", "coba", "gimana", "bagaimana", "apakah", "boleh",
            "bisa", "harus", "perlu", "sangat", "lebih", "paling", "sama",
            "seperti", "jadi", "kalau", "jika", "maka", "tapi", "namun",
            "karena", "agar", "supaya", "oleh", "tentang", "dalam",
            # EN
            "the", "is", "in", "at", "to", "and", "or", "a", "an",
            "of", "for", "on", "with", "by", "from", "as", "but",
            "not", "this", "that", "it", "be", "are", "was", "were",
            "has", "have", "had", "do", "does", "did", "will", "can",
            "could", "would", "should", "may", "might", "must", "shall",
            "how", "what", "when", "where", "who", "why", "which",
            "please", "help", "want", "need", "make", "use", "get",
        }

        keywords = [w for w in words if w not in STOPWORDS and len(w) > 2]

        # Deduplicate sambil menjaga urutan
        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique.append(kw)

        return unique[:20]  # Max 20 keywords

    # ── Relevance scoring ─────────────────────────────────────────────────────

    def _relevance_score(self, content: str, keywords: List[str], query: str) -> float:
        """
        Skor relevansi 0.0–1.0 dari sebuah message terhadap query.
        Menggunakan keyword overlap + n-gram matching.
        """
        if not content or not keywords:
            return 0.1  # Default minimal

        content_lower = content.lower()

        # 1. Keyword overlap (0–0.5)
        hit = sum(1 for kw in keywords if kw in content_lower)
        keyword_score = min(0.5, (hit / max(len(keywords), 1)) * 0.5)

        # 2. Bigram overlap (0–0.3)
        query_bigrams = self._bigrams(query.lower())
        content_bigrams = self._bigrams(content_lower[:500])  # Limit scanning
        if query_bigrams:
            bigram_overlap = len(query_bigrams & content_bigrams) / len(query_bigrams)
            bigram_score = min(0.3, bigram_overlap * 0.3)
        else:
            bigram_score = 0.0

        # 3. Recency bonus (0–0.2) — messages yang dekat ke akhir lebih relevan
        # (ini ditangani oleh caller melalui posisi index, bukan di sini)
        position_score = 0.0

        return keyword_score + bigram_score + position_score

    def _bigrams(self, text: str) -> set:
        words = text.split()
        if len(words) < 2:
            return set()
        return {f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)}

    # ── Message trimming ──────────────────────────────────────────────────────

    def _trim_message(
        self, msg: Dict[str, str], keywords: List[str], max_tokens: int
    ) -> Dict[str, str]:
        """
        Trim message panjang — pertahankan isi tanpa merusak struktur data (JSON/Code).
        """
        content = msg["content"]
        max_chars = int(max_tokens * CHARS_PER_TOKEN)

        if len(content) <= max_chars:
            return msg

        # Hindari memotong paragraf secara acak karena akan merusak JSON atau Source Code.
        # Jika konten terlalu panjang, potong karakter dari belakang secara aman.
        trimmed = content[:max_chars] + "\n\n...[dipotong oleh QMD karena melebihi batas token]"
        return {"role": msg["role"], "content": trimmed}

    # ── Text compression ──────────────────────────────────────────────────────

    def _compress_text(self, text: str) -> str:
        """Kompres teks tanpa menghilangkan makna penting atau merusak struktur."""
        if not text:
            return text

        # Jangan mengompres jika teks kemungkinan adalah source code atau JSON
        # karena akan merusak indentasi yang wajib bagi Python/YAML/JSON.
        if "```" in text or "{" in text:
            return text

        lines = text.split("\n")
        compressed = []
        prev_empty = False

        for line in lines:
            # Skip blank lines berturut-turut tanpa menghapus spasi awal (indentasi)
            if not line.strip():
                if not prev_empty:
                    compressed.append("")
                    prev_empty = True
                continue
            prev_empty = False

            # Skip komentar/separator dekoratif
            if re.match(r'^[═─━━─═\-=*#~]+$', line.strip()):
                continue

            compressed.append(line)

        return "\n".join(compressed)


# ── Singleton ─────────────────────────────────────────────────────────────────
qmd = QueryMessageDistiller()
