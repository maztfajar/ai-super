# 🔍 ANALISIS LENGKAP: Image Upload & VISION_GATE Orchestrator

**Status**: 🐛 **BUG DITEMUKAN** - Image data tidak dikirim ke backend
**Tanggal**: April 14, 2025
**Severity**: HIGH

---

## 📋 RINGKASAN EKSEKUTIF

Image upload memiliki **dua jalur berbeda**:
1. **Jalur Standar** (Berfungsi) ✅ - `/media/upload-image` + `/media/analyze-image`
2. **Jalur Chat Multimodal** (RUSAK) ❌ - Upload → Chat dengan image → VISION_GATE

### Bug Utama:
Frontend **mengupload gambar berhasil**, tetapi **data image TIDAK dikirim ke orchestrator** saat mengirim pesan. Hanya text "[📷 Gambar dikirim]" yang dikirim, tanpa base64 dan mime_type.

---

## 🏗️ ARSITEKTUR IMAGE UPLOAD & MULTIMODAL CHAT

### A. FRONTEND FLOW (React)

```
Chat.jsx (User Upload Image)
    ↓
handleImagePick()
    ↓
api.uploadImage(file)  [POST /media/upload-image]
    ↓
Response: { base64, mime_type, filename, ... }
    ↓
setPendingImage({ base64, mime_type, preview })
    ↓
User klik "Send"
    ↓
sendMessage()
    ├─ imageToSend = pendingImage  ✅
    ├─ Tambah text "[📷 Gambar dikirim] {text}"
    ├─ Panggil: api.chatStream(payload, ...)  ❌ SALAH!
    │  Seharusnya: api.chatStreamMultimodal(payload, imageToSend, ...)
    └─ Image data TERBUANG/TIDAK DIKIRIM
```

**File**: [frontend/src/pages/Chat.jsx](frontend/src/pages/Chat.jsx#L468)

```javascript
// Line 468-481 ← PROBLEM HERE
async function sendMessage() {
  const imageToSend = pendingImage  // ← Ada image data
  
  // ...
  
  abortRef.current = api.chatStream(  // ← WRONG FUNCTION!
    {
      session_id: sessionId,
      message: imageToSend
        ? `[📷 Gambar dikirim] ${text}`  // ← Hanya teks, image TIDAK included
        : text,
      model: selectedOrchestrator,
      use_rag: useRAG,
    },
    // callbacks...
  )
}
```

### B. YANG SEHARUSNYA (Sudah Ada Di useApi.js)

**File**: [frontend/src/hooks/useApi.js](frontend/src/hooks/useApi.js#L251)

```javascript
// Line 251-263 - Function yang SUDAH ADA tapi TIDAK DIGUNAKAN:
chatStreamMultimodal: function(payload, imageData, onChunk, onDone, onSession, onStatus) {
  /**
   * payload: { session_id, message, model, use_rag }
   * imageData: { base64, mime_type } | null
   * Kirim message teks biasa, tapi inject context visual di depan message jika ada gambar.
   */
  // Jika ada gambar, tambahkan sebagai metadata ke payload
  const enriched = Object.assign({}, payload)
  if (imageData) {
    enriched._image_b64  = imageData.base64      // ← ADD IMAGE TO PAYLOAD
    enriched._image_mime = imageData.mime_type   // ← ADD MIME TYPE
  }
  return api.chatStream(enriched, onChunk, onDone, onSession, undefined, onStatus)
}
```

**Solusi**: Ubah Chat.jsx line 475:
```javascript
// SEBELUM (SALAH):
abortRef.current = api.chatStream(payload, ...)

// SESUDAH (BENAR):
abortRef.current = api.chatStreamMultimodal(payload, imageToSend, ...)
```

---

## 🎯 FILE YANG MENANGANI IMAGE UPLOAD

### 1. **FRONTEND - Image Picker & Upload**

| File | Fungsi | Line |
|------|--------|------|
| [frontend/src/pages/Chat.jsx](frontend/src/pages/Chat.jsx#L588) | `handleImagePick()` - Upload gambar ke backend | 588-607 |
| [frontend/src/hooks/useApi.js](frontend/src/hooks/useApi.js#L224) | `uploadImage()` - Call POST /media/upload-image | 224-233 |
| [frontend/src/hooks/useApi.js](frontend/src/hooks/useApi.js#L251) | `chatStreamMultimodal()` - **Kirim dengan image** (TIDAK DIGUNAKAN) | 251-263 |

### 2. **BACKEND - Media Upload API**

| File | Endpoint | Fungsi |
|------|----------|--------|
| [backend/api/media.py](backend/api/media.py#L26) | `POST /media/upload-image` | Terima file, convert base64, simpan disk |
| [backend/api/media.py](backend/api/media.py#L120) | `POST /media/analyze-image` | Analyze gambar langsung (bukan dari chat) |
| [backend/api/media.py](backend/api/media.py#L149) | `GET /media/list` | List media yang sudah diupload |

### 3. **BACKEND - Chat with Image**

| File | Fungsi | Catatan |
|------|--------|---------|
| [backend/api/chat.py](backend/api/chat.py#L119) | `POST /chat/send` - Main chat endpoint | Menerima ChatRequest (tapi tidak ada field image!) |
| [backend/core/orchestrator.py](backend/core/orchestrator.py#L45) | `process()` - Main orchestration | Tidak extract **_image_b64** dari message |
| [backend/core/model_manager.py](backend/core/model_manager.py#L394) | `chat_with_image()` - Vision model | Ada tapi TIDAK dipanggil dari orchestrator |

### 4. **BACKEND - VISION_GATE & Multimodal**

| File | Fungsi | Status |
|------|--------|--------|
| [backend/data/ai_core_prompt.md](backend/data/ai_core_prompt.md#L1) | VISION_GATE definition | Defined as vision specialist |
| [backend/core/capability_map.py](backend/core/capability_map.py) | Model capabilities | "vision" tag available |
| [backend/agents/executor.py](backend/agents/executor.py) | Agent execution | Tidak handle multimodal |

---

## 🔴 ERROR MESSAGES YANG DITEMUKAN


### 1. **Media API Errors**

**File**: [backend/api/media.py](backend/api/media.py)

```python
# Line 145-146: Image Analysis Failed
log.error("Image analysis failed", error=str(e))
raise HTTPException(500, f"Gagal menganalisa gambar: {e}")

# Line 139: Image Too Large
raise HTTPException(413, "Ukuran gambar melebihi 20 MB.")

# Line 38: Not an Image
raise HTTPException(400, "File bukan gambar. Gunakan JPEG, PNG, GIF, atau WebP.")
```

### 2. **Model Manager Errors**

**File**: [backend/core/model_manager.py](backend/core/model_manager.py)

```python
# Line 468-469: chat_with_image Error
log.error("chat_with_image error", model=model_to_use, error=str(e))
return f"❌ Gagal memproses gambar via {model_to_use}: {e}"

# Line 469: No Vision Model Available
return "❌ Tidak ada model vision yang tersedia. Tambahkan model yang mendukung gambar (gemini-2.5-flash, gpt-4o) di menu Integrasi."
```

### 3. **Telegram Bot Errors**

**File**: [backend/integrations/telegram_bot.py](backend/integrations/telegram_bot.py)

```python
# Line 264: Photo Processing Failed
await _send(token, chat_id, "Maaf, gagal memproses gambar. Coba kirim ulang ya!")
```

---

## 🔄 ALUR LENGKAP (YANG SEHARUSNYA TAPI TIDAK BERJALAN)

### A. Ideal Flow: Frontend → Backend → Orchestrator → VISION_GATE

```
1. USER UPLOADS IMAGE (Frontend)
   ├─ Click "Kamera" button
   ├─ Select image file
   ├─ api.uploadImage(file)
   │  └─ POST /media/upload-image
   │     Response: {
   │       "base64": "iVBORw0KGgo...",
   │       "mime_type": "image/png",
   │       "filename": "photo-1.png",
   │       "size_bytes": 245000
   │     }
   ├─ setPendingImage({ base64, mime_type, preview })
   ✅ PREVIEW IMAGE SHOWN
   
2. USER SENDS MESSAGE WITH IMAGE (Frontend)
   ├─ Type text, image pending
   ├─ Click "Send"
   ├─ sendMessage() SHOULD call:
   │  api.chatStreamMultimodal(
   │    { session_id, message, model, use_rag },
   │    imageToSend,  // ← IMAGE DATA
   │    callbacks...
   │  )
   ❌ BUT CURRENTLY CALLS: api.chatStream() WITHOUT IMAGE
   
3. REQUEST TO BACKEND
   POST /chat/send
   Body: {
     session_id: "abc123",
     message: "[📷 Gambar dikirim] Apa ini?",
     model: "orchestrator",
     use_rag: true,
     _image_b64: "iVBORw0KGgo...",    // ← MISSING!
     _image_mime: "image/png"         // ← MISSING!
   }

4. ORCHESTRATOR PREPROCESSING
   orchestrator.process()
     ├─ request_preprocessor.process(message, user_id, session_id)
     ├─ Detect intent: "vision" IF _image_b64 found
     └─ spec.primary_intent = "vision"
   
5. ORCHESTRATOR ROUTING (kalau ada intent vision)
   ├─ if spec.intents contains "vision":
   │  └─ Assign to VISION_GATE agent
   ├─ Select vision model:
   │  ├─ Try: gpt-4o, gemini-2.5-flash, claude-3-vision
   │  └─ Fallback to available vision model
   
6. VISION MODEL PROCESSING
   ├─ model_manager.chat_with_image(
   │    image_b64: "iVBORw0KGgo...",
   │    mime_type: "image/png",
   │    text_prompt: "[Pertanyaan user]",
   │    system_prompt: "[System context]",
   │    history: [...]
   │  )
   ├─ Format message for Vision API:
   │  {
   │    "role": "user",
   │    "content": [
   │      {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgo..."}},
   │      {"type": "text", "text": "[Pertanyaan]"}
   │    ]
   │  }
   ├─ Send to: OpenAI gpt-4o | Gemini | Sumopod
   └─ Return vision analysis result

7. RESPONSE TO FRONTEND
   ├─ Stream chunks (OrchestratorEvent type="chunk")
   ├─ Send done event with model_used metadata
   └─ User sees vision analysis result
```

### B. Actual Current Flow (BUG)

```
1. USER UPLOADS IMAGE ✅
   └─ Image stored in pendingImage state

2. USER SENDS MESSAGE ❌
   ├─ sendMessage() calls api.chatStream() NOT chatStreamMultimodal()
   ├─ Payload: { session_id, message: "[📷 Gambar dikirim]...", model, use_rag }
   ├─ NO _image_b64, NO _image_mime
   └─ Image data LOST

3. REQUEST TO BACKEND ❌
   POST /chat/send
   Body: {
     session_id: "abc123",
     message: "[📷 Gambar dikirim] Apa ini?",
     model: "orchestrator",
     use_rag: true
     // NO IMAGE DATA!
   }

4. ORCHESTRATOR ❌
   ├─ request_preprocessor.process(message)
   ├─ Only sees text: "[📷 Gambar dikirim]..."
   ├─ Does NOT detect "vision" intent
   ├─ Treats as general text chat
   └─ NO VISION GATE INVOLVEMENT

5. REGULAR TEXT PROCESSING ❌
   ├─ Routing to text model (BRAIN, not VISION_GATE)
   ├─ Image context lost
   └─ User gets generic response

## Current Error Flow

sendMessage()
  ↓
api.chatStream(payload, ...)  ← Should be chatStreamMultimodal
  ↓
POST /chat/send with NO image data
  ↓
orchestrator.process() sees only text
  ↓
request_preprocessor doesn't detect vision intent
  ↓
Routes to text model instead of VISION_GATE
  ↓
Lost image analysis capability
```

---

## 🎯 KEMUNGKINAN PENYEBAB KEGAGALAN

### 1. **PRIMARY BUG: Frontend Not Sending Image Data** 🔴 CRITICAL

**Location**: [frontend/src/pages/Chat.jsx](frontend/src/pages/Chat.jsx#L475)

**Masalah**: 
- Frontend upload image berhasil
- Tapi saat send message, gunakan `api.chatStream()` bukan `api.chatStreamMultimodal()`
- Image data tidak dikirim ke backend

**Evidence**:
```javascript
// Chat.jsx line 475 - WRONG
abortRef.current = api.chatStream(
  {
    session_id: sessionId,
    message: imageToSend ? `[📷 Gambar dikirim] ${text}` : text,
    // NO image data in payload!
  },
  ...
)

// Should be (useApi.js line 251-263):
abortRef.current = api.chatStreamMultimodal(
  payload,
  imageToSend,  // ← Image data
  ...
)
```

---

### 2. **SECONDARY BUG: Orchestrator Not Detecting Image Intent**

**Location**: [backend/core/request_preprocessor.py](backend/core/request_preprocessor.py)

**Masalah**: 
- request_preprocessor tidak extract `_image_b64` dari request
- Tidak ada logic untuk detect "vision" intent saat ada image data

**Evidence**: 
Tidak ada pattern matching untuk `_image_b64` atau `image_b64` dalam PREPROCESSOR_PROMPT atau heuristic patterns.

---

### 3. **TERTIARY BUG: ChatRequest Model Tidak Include Image Fields**

**Location**: [backend/api/chat.py](backend/api/chat.py#L18)

**Current**:
```python
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    model: Optional[str] = None
    use_rag: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096
    # NO _image_b64, NO _image_mime!
```

**Should be**:
```python
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    model: Optional[str] = None
    use_rag: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096
    _image_b64: Optional[str] = None      # ← ADD
    _image_mime: Optional[str] = None     # ← ADD
```

---

### 4. **No Vision Intent Detection in Request**

**Location**: [backend/core/request_preprocessor.py](backend/core/request_preprocessor.py)

**Masalah**: 
Preprocessing logic tidak check untuk `_image_b64` field untuk auto-set `primary_intent = "vision"`.

---

### 5. **VISION_GATE Not Integrated in Orchestrator**

**Location**: [backend/core/orchestrator.py](backend/core/orchestrator.py)

**Masalah**:
- Orchestrator punya handler untuk image_generation dan audio_generation
- Tapi NO handler untuk image_analysis / vision task
- Tidak ada routing ke VISION_GATE agent

**Evidence**: 
```python
# Line 96 - Image generation
if primary == "image_generation":
    async for event in self._handle_image_gen(spec, system_prompt, history):
        yield event
    return

# Line 102 - Audio generation
if primary == "audio_generation":
    async for event in self._handle_simple(..., force_agent="audio_gen"):
        yield event
    return

# NO VISION INTENT HANDLER!
if primary == "vision":  # ← THIS IS MISSING!
    async for event in self._handle_vision(spec, system_prompt, history):
        yield event
    return
```

---

## 🐛 ERROR MESSAGES YANG MUNCUL (JIKA ADA)

### Skenario 1: User Upload Image Successfully, Send Chat dengan Image
**Expected**: "Apa ini gambar?"
**Actual**: "Apa ini gambar?" (tanpa analisis visual, cuma jawaban text generic)
**Root Cause**: Image data TIDAK dikirim ke backend

### Skenario 2: User Tries /media/analyze-image Direct
**Status**: ✅ Berfungsi, dapat hasil analisis vision

### Skenario 3: Orchestrator Receives Image (Hypothetical)
**Jika image data sampai tapi tidak ada vision model**:
```
❌ Gagal memproses gambar via [model]: [error]
Atau:
❌ Tidak ada model vision yang tersedia. Tambahkan model yang mendukung gambar (gemini-2.5-flash, gpt-4o) di menu Integrasi.
```

---

## 📊 CAPABILITY MAP (VISION_GATE)

**File**: [backend/core/capability_map.py](backend/core/capability_map.py)

Models dengan capability "vision":
```python
"gpt-4o":              {"text", "vision", "coding", "reasoning", "analysis", "writing"}
"gemini-1.5-pro":      {"text", "vision", "reasoning", "analysis"}
"gemini-2.5-flash":    {"text", "vision", "speed"}
"claude-3-opus":       {"text", "vision", "reasoning"}
"llava":               {"vision", "text"}
"pixtral":             {"vision", "coding", "reasoning"}
"qwen":                {"text", "vision", "coding"}
```

---

## 🔧 PERBAIKAN YANG DIPERLUKAN

### Fix #1: Frontend - Use chatStreamMultimodal (CRITICAL)
**File**: [frontend/src/pages/Chat.jsx](frontend/src/pages/Chat.jsx#L475)

```javascript
// SEBELUM
abortRef.current = api.chatStream(
  {
    session_id: sessionId,
    message: imageToSend ? `[📷 Gambar dikirim] ${text}` : text,
    model: selectedOrchestrator,
    use_rag: useRAG,
  },
  ...
)

// SESUDAH
abortRef.current = imageToSend 
  ? api.chatStreamMultimodal(
      {
        session_id: sessionId,
        message: text,  // Just the text, not "[📷 Gambar dikirim]..."
        model: selectedOrchestrator,
        use_rag: useRAG,
      },
      imageToSend,
      ...
    )
  : api.chatStream(
      {
        session_id: sessionId,
        message: text,
        model: selectedOrchestrator,
        use_rag: useRAG,
      },
      ...
    )
```

### Fix #2: Backend - Add Image Fields to ChatRequest
**File**: [backend/api/chat.py](backend/api/chat.py#L18)

```python
class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    model: Optional[str] = None
    use_rag: bool = True
    temperature: float = 0.7
    max_tokens: int = 4096
    _image_b64: Optional[str] = None      # ← ADD
    _image_mime: Optional[str] = None     # ← ADD
```

### Fix #3: Backend - Extract Image in Chat Endpoint
**File**: [backend/api/chat.py](backend/api/chat.py#L119)

Extract image data from request and pass to orchestrator:
```python
async def chat_send(req: ChatRequest, ...):
    # ... existing code ...
    
    # Extract multimodal data
    image_b64 = req._image_b64 or None
    image_mime = req._image_mime or None
    
    # Pass to orchestrator
    async for event in orchestrator.process(
        message=req.message,
        user_id=user.id,
        session_id=session.id,
        **other_params,
        image_b64=image_b64,        # ← ADD
        image_mime=image_mime,      # ← ADD
    ):
        yield event
```

### Fix #4: Backend - Add Image Params to Orchestrator
**File**: [backend/core/orchestrator.py](backend/core/orchestrator.py#L45)

```python
async def process(
    self,
    message: str,
    user_id: str,
    session_id: str,
    user_model_choice: Optional[str] = None,
    system_prompt: str = "",
    history: List[Dict] = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    use_rag: bool = True,
    image_b64: Optional[str] = None,        # ← ADD
    image_mime: Optional[str] = None,       # ← ADD
    include_tool_logs: bool = True,
) -> AsyncGenerator[OrchestratorEvent, None]:
```

### Fix #5: Backend - Handle Vision Intent
**File**: [backend/core/orchestrator.py](backend/core/orchestrator.py#L95)

Add after line 103 (before simple message check):
```python
# Auto-detect vision intent if image provided
if image_b64 and image_mime:
    spec.intents.append("vision")
    spec.primary_intent = "vision"

# ─── VISION ANALYSIS HANDLER ──────────────────
if spec.primary_intent == "vision":
    async for event in self._handle_vision(
        spec, system_prompt, history, image_b64, image_mime, temperature, max_tokens
    ):
        yield event
    return
```

### Fix #6: Backend - Implement _handle_vision Method
**File**: [backend/core/orchestrator.py](backend/core/orchestrator.py)

```python
async def _handle_vision(
    self,
    spec: TaskSpecification,
    system_prompt: str,
    history: list,
    image_b64: str,
    image_mime: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[OrchestratorEvent, None]:
    """Handle vision/image analysis tasks using VISION_GATE."""
    yield OrchestratorEvent("status", "👁️ Menganalisa gambar dengan VISION_GATE...")
    
    try:
        image_analysis = await model_manager.chat_with_image(
            image_b64=image_b64,
            mime_type=image_mime,
            text_prompt=spec.original_message,
            system_prompt=system_prompt,
            history=history,
        )
        
        yield OrchestratorEvent("chunk", image_analysis)
        yield OrchestratorEvent("done", "", {
            "model_used": "VISION_GATE",
            "capability_used": "vision"
        })
    except Exception as e:
        log.error("Vision analysis failed", error=str(e))
        yield OrchestratorEvent("error", f"👁️ Gagal menganalisa gambar: {e}")
```

---

## 📚 REFERENSI FILE

### Frontend Files
- [frontend/src/pages/Chat.jsx](frontend/src/pages/Chat.jsx) - Image upload UI & message sending
- [frontend/src/hooks/useApi.js](frontend/src/hooks/useApi.js) - API client functions

### Backend Files - Media API
- [backend/api/media.py](backend/api/media.py) - Image upload/analysis endpoints

### Backend Files - Chat & Orchestration
- [backend/api/chat.py](backend/api/chat.py) - Chat endpoint
- [backend/core/orchestrator.py](backend/core/orchestrator.py) - Main orchestration engine
- [backend/core/request_preprocessor.py](backend/core/request_preprocessor.py) - Intent detection
- [backend/core/model_manager.py](backend/core/model_manager.py) - Vision model integration
- [backend/core/capability_map.py](backend/core/capability_map.py) - Model capabilities

### Backend Files - Configuration & Definition
- [backend/data/ai_core_prompt.md](backend/data/ai_core_prompt.md) - VISION_GATE definition
- [backend/agents/executor.py](backend/agents/executor.py) - Agent execution
- [backend/agents/agent_registry.py](backend/agents/agent_registry.py) - Agent definitions

### Integration Files
- [backend/integrations/telegram_bot.py](backend/integrations/telegram_bot.py) - Telegram image handling (reference implementation)

---

## ✅ TESTING CHECKLIST

Untuk memverifikasi fixes:

- [ ] Frontend upload image returns base64 + mime_type
- [ ] Frontend sendMessage() with image calls chatStreamMultimodal()
- [ ] Backend /chat/send receives _image_b64 and _image_mime
- [ ] ChatRequest model includes optional image fields
- [ ] Orchestrator detects vision intent when image present
- [ ] Orchestrator routes to VISION_GATE handler
- [ ] model_manager.chat_with_image() gets called with correct params
- [ ] Vision model returns analysis result
- [ ] Frontend displays vision analysis in chat
- [ ] Error handling works if no vision model available
- [ ] Works across all vision models: gpt-4o, gemini-2.5-flash, claude-3
- [ ] Telegram image handling still works (already functional at integrations/telegram_bot.py)

---

## 📝 SUMMARY

| Aspek | Status | Location |
|-------|--------|----------|
| **Image Upload (Direct)** | ✅ Berfungsi | /media/upload-image |
| **Image Analysis (Direct)** | ✅ Berfungsi | /media/analyze-image |
| **Image in Chat (Multimodal)** | ❌ RUSAK | Chat.jsx → NOT sending image to backend |
| **VISION_GATE Definition** | ✅ Ada | ai_core_prompt.md |
| **VISION_GATE Routing** | ❌ Tidak ada | Orchestrator tidak implement |
| **Vision Model Integration** | ✅ Ada | model_manager.chat_with_image() |
| **Telegram Image Handler** | ✅ Berfungsi | telegram_bot.py |

**Root Cause**: Frontend menggunakan `api.chatStream()` bukan `api.chatStreamMultimodal()`, sehingga image data tidak dikirim ke backend.<br>
**Impact**: User tidak bisa analiza gambar dalam chat view multimodal<br>
**Severity**: HIGH - Core multimodal feature broken<br>
**Fix Effort**: MEDIUM - Requires updates in 4-5 files
