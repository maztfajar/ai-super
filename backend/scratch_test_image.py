import asyncio
import httpx
import os
import sys
from dotenv import load_dotenv

# Load .env
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

async def test_image():
    host = os.environ.get("SUMOPOD_HOST", "https://ai.sumopod.com/v1")
    api_key = os.environ.get("SUMOPOD_API_KEY", "")
    
    print(f"SUMOPOD_HOST: {host}")
    print(f"SUMOPOD_API_KEY: {api_key[:8]}...{api_key[-4:] if api_key else ''}")
    
    if not api_key:
        print("API Key tidak ditemukan!")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Coba dengan model "flux"
    payload = {
        "model": "flux",
        "prompt": "A close-up portrait of an elderly fisherman",
        "n": 1,
        "size": "1024x1024",
        "response_format": "url",
    }
    
    print("\nMencoba request ke Sumopod...")
    url = f"{host.rstrip('/')}/images/generations"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            print(f"Status Code: {resp.status_code}")
            try:
                data = resp.json()
                print("Response JSON:")
                import json
                print(json.dumps(data, indent=2))
            except Exception:
                print(f"Response Text (bukan JSON): {resp.text[:500]}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_image())
