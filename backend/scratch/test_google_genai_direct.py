import asyncio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Load .env
from dotenv import load_dotenv
load_dotenv("/home/bamuskal/Documents/ai-super/.env")

import google.genai as genai
from google.genai import types as genai_types

api_key = os.environ.get("GOOGLE_API_KEY", "")
print(f"API Key set: {'YES' if api_key and len(api_key) > 20 else 'NO'}")
print(f"API Key prefix: {api_key[:10]}...")

try:
    client = genai.Client(api_key=api_key)
    chat = client.chats.create(model="gemini-2.0-flash-lite", history=[])
    response = chat.send_message("Say: HELLO WORLD")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
