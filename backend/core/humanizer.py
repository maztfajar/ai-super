"""
Humanizer Skill (Anti AI Slop)
==============================
Sistem ini bertugas memoles output AI agar tidak terlihat kaku atau seperti "robot".
Ia mendeteksi kecenderungan pola bahasa mesin dan memaksakan aturan gaya bahasa
yang lebih natural, kasual, dan layaknya manusia.

Cara kerja:
- Menginjeksi "Anti-Slop System Prompt" ke dalam message pipeline secara dinamis
- Menghindari kata-kata dramatis/klise AI (misal: "Penting untuk diingat", "Sebagai AI", "Menyelami lebih dalam")
- Membuat struktur paragraf lebih asimetris (seperti cara manusia menulis)
- Diterapkan pada path eksekusi orchestrator untuk tugas penulisan/komunikasi
"""

import re
from typing import List, Dict, Tuple
import structlog

log = structlog.get_logger()

# Daftar kata/frasa khas AI yang harus dihindari (AI Slop)
AI_SLOP_PATTERNS = [
    "Penting untuk diingat",
    "Sebagai model bahasa",
    "Sebagai AI",
    "Menyelami lebih dalam",
    "Kesimpulannya",
    "Mari kita jelajahi",
    "Tentu saja!",
    "Bisa dibilang",
    "Dalam lanskap",
    "Di era digital ini",
    "Secara inheren",
    "Perlu digarisbawahi",
    "Mengungkap misteri",
    "Tidak dapat dipungkiri",
]

ANTI_SLOP_PROMPT = """
[CRITICAL SYSTEM INSTRUCTION: HUMANIZER SKILL ACTIVE]
PENTING: Jangan gunakan bahasa kaku khas AI (AI Slop). Tulis dengan gaya bahasa natural layaknya manusia yang ahli namun kasual.
ATURAN WAJIB:
1. HINDARI frasa klise seperti: "Penting untuk diingat", "Mari kita jelajahi", "Di era digital ini", "Sebagai AI", "Kesimpulannya", "Tentu saja!".
2. Jangan gunakan struktur yang terlalu rapi atau simetris (misal: selalu mengawali paragraf dengan transisi kaku).
3. Langsung to the point. Jangan bertele-tele atau menambahkan pengantar yang tidak perlu.
4. Gunakan variasi panjang kalimat. Manusia kadang menulis kalimat pendek. Kadang panjang.
5. Bersikaplah beropini jika sesuai konteks, tidak perlu selalu mengambil posisi netral yang membosankan.
6. Hindari dramatisasi berlebihan (hyperbole) kecuali diminta.
"""

class Humanizer:
    """Anti-Slop Engine untuk Orchestrator."""

    def __init__(self):
        self.enabled = True
        self.slop_patterns = [re.compile(p, re.IGNORECASE) for p in AI_SLOP_PATTERNS]

    def detect_slop(self, text: str) -> float:
        """
        Mendeteksi seberapa banyak AI slop di sebuah teks.
        Mengembalikan nilai 0.0 (bersih) hingga 1.0 (sangat kaku/slop).
        """
        if not text:
            return 0.0
            
        hits = 0
        for pattern in self.slop_patterns:
            if pattern.search(text):
                hits += 1
                
        # Scoring: 3+ hits = 1.0 (high slop)
        return min(1.0, hits / 3.0)

    def inject_anti_slop(self, messages: List[Dict[str, str]], intent: str = "general") -> Tuple[List[Dict[str, str]], bool]:
        """
        Menginjeksi prompt Humanizer ke dalam messages jika intent relevan (writing/general/research).
        Mengembalikan (modified_messages, is_injected).
        """
        if not self.enabled:
            return messages, False

        # Jangan injeksi untuk tugas coding atau system karena bisa merusak format teknis
        if intent in ["coding", "system", "file_operation"]:
            return messages, False

        # Cari system prompt terakhir, atau jika tidak ada, tambahkan
        injected = False
        new_messages = []
        
        for msg in messages:
            if msg["role"] == "system" and not injected:
                # Append ke system prompt
                new_msg = msg.copy()
                new_msg["content"] = msg["content"] + "\n\n" + ANTI_SLOP_PROMPT
                new_messages.append(new_msg)
                injected = True
            else:
                new_messages.append(msg)

        if not injected:
            # Jika tidak ada system prompt, sisipkan di awal
            new_messages.insert(0, {"role": "system", "content": ANTI_SLOP_PROMPT})
            injected = True

        if injected:
            log.debug("Humanizer: Anti-slop prompt injected", intent=intent)

        return new_messages, injected

humanizer = Humanizer()
