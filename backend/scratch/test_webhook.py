import asyncio
import httpx

async def test_webhook():
    payload = {
        "update_id": 123456789,
        "message": {
            "message_id": 1,
            "from": {
                "id": 111111111,
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": 111111111,
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": 1620000000,
            "text": "Buatkan saya gambar anjing"
        }
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:7860/api/integrations/telegram/webhook", json=payload)
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text}")

if __name__ == "__main__":
    asyncio.run(test_webhook())
