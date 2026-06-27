from httpx2 import AsyncClient

ADA = {"basics": {"full_name": "Ada"}}
GRACE = {"basics": {"full_name": "Grace"}}


async def test_get_current_returns_404_when_empty(client: AsyncClient) -> None:
    response = await client.get("/profile")
    assert response.status_code == 404


async def test_put_creates_versions(client: AsyncClient) -> None:
    first = await client.put("/profile", json=ADA)
    assert first.status_code == 201
    assert first.json()["version_number"] == 1
    second = await client.put("/profile", json=GRACE)
    assert second.status_code == 201
    assert second.json()["version_number"] == 2


async def test_put_identical_returns_200_without_new_version(
    client: AsyncClient,
) -> None:
    await client.put("/profile", json=ADA)
    again = await client.put("/profile", json=ADA)
    assert again.status_code == 200
    assert again.json()["version_number"] == 1


async def test_get_current_returns_latest(client: AsyncClient) -> None:
    await client.put("/profile", json=ADA)
    await client.put("/profile", json=GRACE)
    response = await client.get("/profile")
    assert response.status_code == 200
    body = response.json()
    assert body["version_number"] == 2
    assert body["data"]["basics"]["full_name"] == "Grace"


async def test_list_versions(client: AsyncClient) -> None:
    await client.put("/profile", json=ADA)
    await client.put("/profile", json=GRACE)
    response = await client.get("/profile/versions")
    assert response.status_code == 200
    items = response.json()
    assert [v["version_number"] for v in items] == [2, 1]
    assert all("data" not in v for v in items)


async def test_get_version_not_found(client: AsyncClient) -> None:
    response = await client.get("/profile/versions/99")
    assert response.status_code == 404


async def test_invalid_body_returns_422(client: AsyncClient) -> None:
    response = await client.put("/profile", json={"basics": {}})
    assert response.status_code == 422


async def test_restore_creates_new_version(client: AsyncClient) -> None:
    await client.put("/profile", json=ADA)
    await client.put("/profile", json=GRACE)
    response = await client.post("/profile/versions/1/restore")
    assert response.status_code == 201
    assert response.json()["version_number"] == 3
    assert response.json()["data"]["basics"]["full_name"] == "Ada"


async def test_restore_missing_returns_404(client: AsyncClient) -> None:
    response = await client.post("/profile/versions/99/restore")
    assert response.status_code == 404
