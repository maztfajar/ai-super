import httpx
import os

async def check_docker():
    socket_path = "/var/run/docker.sock"
    if not os.path.exists(socket_path):
        print("Socket not found")
        return
    
    transport = httpx.AsyncHTTPTransport(uds=socket_path)
    async with httpx.AsyncClient(transport=transport, base_url="http://docker") as c:
        r = await c.get("/containers/json?all=true")
        for ct in r.json():
            print(f"Container: {ct.get('Names')} | Image: {ct.get('Image')} | State: {ct.get('State')}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(check_docker())
