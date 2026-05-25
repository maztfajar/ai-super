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
    "ar": "ar-SA-HamedNeural",
    "jp": "ja-JP-KeitaNeural",
    "jv": "jv-ID-DimasNeural",
}

@router.get("/tts")
async def text_to_speech(
    text: str = Query(..., description="The text to convert to speech"),
    lang: str = Query("id", description="Language code (id, en, jp, ar, jv)"),
):
    """
    Convert text to speech using Microsoft Edge TTS / Model Manager and return as an MP3 stream.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        from core.model_manager import model_manager
        from agents.agent_registry import agent_registry
        
        # Resolve audio_gen model
        audio_model = agent_registry.resolve_model_for_agent("audio_gen")
        
        log.info("Generating TTS via ModelManager", text_len=len(text), lang=lang, audio_model=audio_model)
        
        audio_bytes = await model_manager.generate_speech(text, voice_or_model=audio_model, lang=lang)
        
        return StreamingResponse(
            io.BytesIO(audio_bytes), 
            media_type="audio/mpeg",
            headers={"Content-Disposition": f'attachment; filename="tts.mp3"'}
        )
        
    except Exception as e:
        log.error("TTS Generation Error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: {str(e)}")
