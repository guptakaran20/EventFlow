import asyncio
import httpx
from app.main import app
from httpx import ASGITransport, AsyncClient

async def run():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/api/v1/auth/verify")
        print("No header:", r1.status_code, r1.text)
        r2 = await client.get("/api/v1/auth/verify", headers={"X-EventFlow-API-Key": "wrong-key"})
        print("Wrong header:", r2.status_code, r2.text)

asyncio.run(run())
