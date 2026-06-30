from httpx2 import AsyncClient


async def test_discover_returns_summary(client: AsyncClient) -> None:
    await client.put("/search-criteria", json={"active_sources": ["mock"]})
    response = await client.post("/jobs/discover")
    assert response.status_code == 200
    body = response.json()
    assert body["created"] >= 1
    assert any(source["source"] == "mock" for source in body["sources"])


async def test_list_jobs_returns_persisted(client: AsyncClient) -> None:
    await client.put("/search-criteria", json={"active_sources": ["mock"]})
    await client.post("/jobs/discover")
    response = await client.get("/jobs")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 1
    assert all("title" in job for job in jobs)
    assert all("raw" not in job for job in jobs)


async def test_discover_with_no_active_sources_creates_nothing(client: AsyncClient) -> None:
    await client.put("/search-criteria", json={"active_sources": []})
    response = await client.post("/jobs/discover")
    assert response.status_code == 200
    assert response.json()["created"] == 0


async def test_list_jobs_respects_limit(client: AsyncClient) -> None:
    await client.put("/search-criteria", json={"active_sources": ["mock"]})
    await client.post("/jobs/discover")  # mock yields two jobs
    response = await client.get("/jobs", params={"limit": 1})
    assert response.status_code == 200
    assert len(response.json()) == 1
