from httpx2 import AsyncClient

PY = {"keywords": ["python"]}
RUST = {"keywords": ["rust"]}


async def test_get_returns_404_when_unset(client: AsyncClient) -> None:
    response = await client.get("/search-criteria")
    assert response.status_code == 404


async def test_put_creates_returns_201_then_update_returns_200(client: AsyncClient) -> None:
    first = await client.put("/search-criteria", json=PY)
    assert first.status_code == 201
    second = await client.put("/search-criteria", json=RUST)
    assert second.status_code == 200


async def test_get_returns_current_after_put(client: AsyncClient) -> None:
    await client.put("/search-criteria", json=PY)
    response = await client.get("/search-criteria")
    assert response.status_code == 200
    assert response.json()["data"]["keywords"] == ["python"]


async def test_put_invalid_body_returns_422(client: AsyncClient) -> None:
    response = await client.put("/search-criteria", json={"min_salary": -1})
    assert response.status_code == 422
