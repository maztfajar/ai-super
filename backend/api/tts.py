from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
import edge_tts
import io
import structlog
import anyio

router = APIRouter()
log = structlog.get_logger()

# Mapping of language codes to edge-tts voices
VOICES = {
    "id": "id-ID-ArdiNeural",
    "en": "en-US-GuyNeural",
    "jp": "ja-JP-KeitaNeural",
}

@router.get("/tts")
async def text_to_speech(
    text: str = Query(..., description="The text to convert to speech"),
    lang: str = Query("id", description="Language code (id, en, jp)"),
):
    """
    Convert text to speech using Microsoft Edge TTS and return as an MP3 stream.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    voice = VOICES.get(lang, VOICES["id"])
    
    try:
        log.info("Generating TTS", text_len=len(text), lang=lang, voice=voice)
        
        communicate = edge_tts.Communicate(text, voice)
        
        # We need to collect the audio in a buffer
        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])
        
        audio_data.seek(0)
        
        return StreamingResponse(
            audio_data, 
            media_type="audio/mpeg",
            headers={"Content-Disposition": f'attachment; filename="tts.mp3"'}
        )
        
    except Exception as e:
        log.error("TTS Generation Error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: {str(e)}")
