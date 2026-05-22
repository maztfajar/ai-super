"""
Media Tools — Image generation, vision, and audio processing.
"""
import urllib.parse
from core.model_manager import model_manager
from core.capability_map import capability_map
import structlog

log = structlog.get_logger()

async def generate_image(prompt: str, model: str = None) -> str:
    """
    Generate an image from a text prompt.
    
    Args:
        prompt: Detailed description of the image to generate.
        model: Optional model ID to use (e.g. 'pollinations/flux', 'dall-e-3').
    
    Returns:
        A markdown string with the image URL or an error message.
    """
    if not prompt:
        return "❌ Error: Prompt tidak boleh kosong."
        
    log.info("Tool generate_image called", prompt=prompt[:100], model=model)
    
    try:
        # Use provided model or find the best available
        target_model = model
        if not target_model:
            target_model = capability_map.find_best_model({"image_gen"})
            
        generated_url = await model_manager.generate_image(
            prompt=prompt,
            model=target_model
        )
        
        if not generated_url:
            return "❌ Gagal generate gambar. Tidak ada provider image yang tersedia atau limit tercapai."
            
        return f"✅ **Gambar berhasil dibuat!**\n\n![Hasil Gambar]({generated_url})\n\nPrompt: _{prompt}_"
        
    except Exception as e:
        log.error("Tool generate_image failed", error=str(e))
        return f"❌ Terjadi kesalahan saat generate gambar: {str(e)}"
