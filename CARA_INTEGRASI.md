# Cara Integrasi Human Logic Engine ke ai-super

## File yang perlu diganti

### 1. `data/ai_core_prompt.md`
Ganti dengan file `ai_core_prompt.md` dari paket ini.

Isinya sudah mengandung modul **HUMAN LOGIC ENGINE** yang mengajarkan Orchestra cara:
- Membaca emosi & situasi pengguna sebelum menjawab
- Menggunakan empati sebelum solusi
- Menyesuaikan nada secara organik
- Mengingat konteks percakapan
- Berpikir dengan alur manusiawi (Dengarkan → Rasakan → Pahami → Bertindak)

---

### 2. `backend/core/request_preprocessor.py`
Ganti dengan file `request_preprocessor.py` dari paket ini.

Yang ditambahkan (v3.0 vs v2.1):

**Class baru: `EmotionalState`**
Menyimpan kondisi emosional pengguna hasil analisis:
- `dominant_emotion` — emosi utama (frustrated, excited, anxious, confused, dll)
- `intensity` — seberapa kuat (0.0–1.0)
- `implied_need` — kebutuhan tersirat (needs_validation, venting, dll)
- `tone_hint` — petunjuk nada untuk model
- `has_time_pressure` — ada urgensi waktu
- `needs_acknowledgment` — butuh divalidasi emosinya dulu

**Class baru: `HumanContextLayer`**
Lapisan analisis manusiawi yang berjalan sebelum klasifikasi intent teknis.
Menggunakan pattern matching berbasis kata-kata emosional dalam dua bahasa (ID/EN).

**`TaskSpecification` diperluas**
Sekarang menyertakan `emotional_state`, `implied_need`, dan `tone_hint`
yang bisa dibaca oleh orchestrator untuk menyesuaikan cara respons.

**`_enrich()` diperluas**
Jika user frustrasi/lelah/cemas → `quality_priority` otomatis dinaikkan ke "high"
agar model yang dipilih lebih matang dalam merespons.

---

## Cara orchestrator menggunakan data emosi

Di `backend/core/orchestrator.py`, setelah memanggil `request_preprocessor.process()`,
kamu bisa meneruskan informasi emosi ke system prompt model:

```python
spec = await request_preprocessor.process(message, ...)

# Tambahkan context emosi ke system prompt jika relevan
emotional_hint = ""
if spec.emotional_state.needs_acknowledgment:
    emotional_hint = f"\n[CATATAN INTERNAL: Pengguna terlihat {spec.emotional_state.dominant_emotion}. "
    emotional_hint += f"Akui kondisi mereka dulu sebelum menjawab. "
    emotional_hint += f"Gunakan nada: {spec.tone_hint}]"

if spec.emotional_state.has_time_pressure:
    emotional_hint += "\n[Pengguna sedang terburu-buru. Berikan jawaban ringkas dan langsung ke solusi.]"

# Inject ke system prompt model yang dipilih
final_system_prompt = base_system_prompt + emotional_hint
```

---

## Tidak ada breaking change
Semua fast-path, cache, fallback, dan routing logic dari v2.1 dipertahankan.
Penambahan bersifat additive — tidak mengubah behavior yang sudah ada.
