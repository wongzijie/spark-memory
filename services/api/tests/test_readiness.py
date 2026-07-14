import asyncio


async def test_readiness_checks_postgres_and_redis(client):
    async with asyncio.timeout(5):
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
