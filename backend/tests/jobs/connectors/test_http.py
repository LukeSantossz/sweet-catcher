from collections.abc import Awaitable, Callable

import httpx2
import pytest

from app.jobs.connectors.http import PoliteClient


def _silent_sleep_spy() -> tuple[list[float], Callable[[float], Awaitable[None]]]:
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    return sleeps, sleep


async def test_polite_client_sends_identifiable_user_agent() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen["user_agent"] = request.headers["user-agent"]
        return httpx2.Response(200, text="ok")

    client = PoliteClient(transport=httpx2.MockTransport(handler), min_interval=0.0)
    await client.get_text("https://example.test/jobs")

    assert "sweet-catcher" in seen["user_agent"].lower()


async def test_polite_client_retries_transient_error_then_returns_body() -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx2.Response(503, text="busy")
        return httpx2.Response(200, text="ok")

    _, sleep = _silent_sleep_spy()
    client = PoliteClient(transport=httpx2.MockTransport(handler), min_interval=0.0, sleep=sleep)

    body = await client.get_text("https://example.test/jobs")

    assert body == "ok"
    assert calls["n"] == 2


async def test_polite_client_raises_after_exhausting_retries() -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(503, text="busy")

    _, sleep = _silent_sleep_spy()
    client = PoliteClient(
        transport=httpx2.MockTransport(handler), max_retries=2, min_interval=0.0, sleep=sleep
    )

    with pytest.raises(httpx2.HTTPStatusError):
        await client.get_text("https://example.test/jobs")

    assert calls["n"] == 3  # initial attempt + 2 retries


async def test_polite_client_does_not_retry_on_client_error() -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(404, text="missing")

    _, sleep = _silent_sleep_spy()
    client = PoliteClient(transport=httpx2.MockTransport(handler), min_interval=0.0, sleep=sleep)

    with pytest.raises(httpx2.HTTPStatusError):
        await client.get_text("https://example.test/jobs")

    assert calls["n"] == 1  # no retry on a 4xx


async def test_polite_client_waits_minimum_interval_between_requests_to_same_host() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, text="ok")

    sleeps, sleep = _silent_sleep_spy()

    def frozen_clock() -> float:
        return 1000.0  # time never advances, so the second call must wait the full interval

    client = PoliteClient(
        transport=httpx2.MockTransport(handler),
        min_interval=1.5,
        sleep=sleep,
        clock=frozen_clock,
    )

    await client.get_text("https://example.test/a")
    await client.get_text("https://example.test/b")

    assert sleeps == [1.5]
