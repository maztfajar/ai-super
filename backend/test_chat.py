import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Get auth token using super admin
        login_res = await client.post("http://localhost:7860/api/auth/login", json={"username":"admin", "password":"password"})
        if login_res.status_code != 200:
            print("Login failed", login_res.text)
            return
        token = login_res.json()["token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"message": "cek ram", "model": "auto-orchestrator", "use_rag": False}
        
        print("Sending chat request...")
        async with client.stream("POST", "http://localhost:7860/api/chat/send", json=payload, headers=headers) as response:
            print("Status:", response.status_code)
            async for chunk in response.aiter_text():
                print(chunk, end="", flush=True)

asyncio.run(main())
