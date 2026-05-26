import asyncio
import re
import sys
import os

# Adjust path to import local modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import AsyncSessionLocal
from db.models import Message
from sqlmodel import select
from core.model_manager import model_manager

async def fix_existing_session():
    print("Starting image fix for session 036e9aa6-7bcf-4890-8909-15e0b1e2b6e6...")
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Message).where(Message.session_id == '036e9aa6-7bcf-4890-8909-15e0b1e2b6e6', Message.role == 'assistant'))
        messages = res.scalars().all()
        if not messages:
            print("No assistant messages found for this session!")
            return
            
        for m in messages:
            content = m.content
            fake_img_pattern = r'!\[(.*?)\]\((https?://[^\s)]+)\)'
            matches = re.findall(fake_img_pattern, content)
            if matches:
                print(f"Found {len(matches)} fake images in message {m.id}")
                for alt_text, fake_url in matches:
                    hallucination_domains = ["imgur.com", "unsplash.com", "placeholder", "dummy", "example.com", "picsum.photos", "google.com/imgres"]
                    if any(dom in fake_url.lower() for dom in hallucination_domains):
                        prompt = alt_text.replace("Ilustrasi", "").replace("ilustrasi", "").strip("1234567890:.- ")
                        if not prompt:
                            prompt = f"Legenda Tangkuban Perahu - {alt_text}"
                        
                        # Add descriptive context
                        prompt = f"Legenda Tangkuban Perahu: {prompt}, children book illustration style, colorful"
                        
                        print(f"Generating real image for prompt: '{prompt}'")
                        try:
                            real_url = await model_manager.generate_image(prompt, model="pollinations/auto")
                            if real_url:
                                content = content.replace(fake_url, real_url)
                                print(f"Successfully replaced {fake_url} with {real_url}")
                        except Exception as e:
                            print(f"Failed to generate image: {e}")
                
                m.content = content
                db.add(m)
                await db.commit()
                print("Session successfully updated!")
            else:
                print("No fake images detected in this message.")

if __name__ == "__main__":
    asyncio.run(fix_existing_session())
