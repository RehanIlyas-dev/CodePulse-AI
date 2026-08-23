import time

from httpx import AsyncClient


async def test_health_check(async_client: AsyncClient):
    # --> Test the root endpoint for health check
    response = await async_client.get("/docs")
    assert response.status_code == 200


async def test_guardrails_unsupported_language(async_client: AsyncClient):
   # --> Verify system rejects unsupported languages gracefully.
    payload = {
        "title": "unsupported lang test",
        "code": "print('Hello World')",
        "language": "unsupported_lang"
    }
    response = await async_client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 400


async def test_guardrails_payload_size_limit(async_client: AsyncClient):
   # --> Verify system rejects code snippets that exceed the byte threshold.
    large_code = "x = 1\n" * 100000  # Exceeds byte threshold
    payload = {
        "title": "oversize test",
        "code": large_code,
        "language": "python"
    }
    response = await async_client.post("/api/v1/analyze", json=payload)
    assert response.status_code in [400, 413]


async def test_job_status_not_found(async_client: AsyncClient):
    # --> Verify system handles invalid job UUID lookups cleanly.
    invalid_uuid = "00000000-0000-0000-0000-000000000000"
    response = await async_client.get(f"/api/v1/jobs/{invalid_uuid}")
    assert response.status_code == 404


async def test_scans_endpoint_db_roundtrip(async_client: AsyncClient, authed_client: AsyncClient):
    # --> History is private: anon gets 401, signed-in user gets their own list.
    saved = async_client.headers.get("Authorization")
    del async_client.headers["Authorization"]
    anon = await async_client.get("/api/v1/scans?limit=5")
    async_client.headers["Authorization"] = saved
    assert anon.status_code == 401

    response = await authed_client.get("/api/v1/scans?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_repo_scans_endpoint_db_roundtrip(authed_client: AsyncClient):
    # --> Same privacy rule for repo scans.
    response = await authed_client.get("/api/v1/repo-scans?limit=5")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_rate_limiter_returns_429(async_client: AsyncClient, redis_client):
    # --> Hammer /analyze past the 10 req/min limit; rejected requests still count.
    payload = {"title": "rl", "code": "x = 1", "language": "definitely_not_a_lang"}
    codes = [ (await async_client.post("/api/v1/analyze", json=payload)).status_code for _ in range(12) ]

    assert codes[0] == 400                    
    assert 429 in codes                         

    # Cleanup so this test doesn't starve the others in the same minute
    if redis_client is not None:
        await redis_client.delete(f"rate_limit:127.0.0.1:{int(time.time()) // 60}")
