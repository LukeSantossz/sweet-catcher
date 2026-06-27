from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/health")  # type: ignore[attr-defined]
    assert response.status_code == 200  # type: ignore[attr-defined]
    assert response.json() == {"status": "ok"}  # type: ignore[attr-defined]
