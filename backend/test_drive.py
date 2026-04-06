import sys
import os
import asyncio
from dotenv import load_dotenv

sys.path.append("/home/maztfajar/Downloads/pitakonku/backend")
load_dotenv("/home/maztfajar/Downloads/pitakonku/backend/.env")

from integrations.google_drive import list_drive_folders

async def test():
    try:
        folders = await list_drive_folders()
        print(f"Total folders found: {len(folders)}")
        for f in folders:
            print(f"Name: {f['name']} | ID: {f['id']} | Parents: {f.get('parents', [])}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
