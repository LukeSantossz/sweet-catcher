from collections.abc import Awaitable, Callable

import httpx2
import pytest

from app.jobs.connectors.http import PoliteClient


def _silent_sleep_spy() -> tuple[list[float], Callable[[float], Awaitable[None]]]:
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)

    return sleeps, sleep


def _seq_clock(values: list[float]) -> Callable[[], float]:
    iterator = iter(values)

    def clock() -> float:
        return next(iterator)

    return clock


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


async def test_polite_client_retries_on_transport_error_then_returns_body() -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx2.ConnectError("boom")
        return httpx2.Response(200, text="ok")

    _, sleep = _silent_sleep_spy()
    client = PoliteClient(transport=httpx2.MockTransport(handler), min_interval=0.0, sleep=sleep)

    assert await client.get_text("https://example.test/x") == "ok"
    assert calls["n"] == 2


async def test_polite_client_raises_transport_error_after_exhausting_retries() -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        raise httpx2.ConnectError("down")

    _, sleep = _silent_sleep_spy()
    client = PoliteClient(
        transport=httpx2.MockTransport(handler), max_retries=2, min_interval=0.0, sleep=sleep
    )

    with pytest.raises(httpx2.TransportError):
        await client.get_text("https://example.test/x")

    assert calls["n"] == 3


async def test_polite_client_uses_exponential_backoff_between_retries() -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(503 if calls["n"] <= 3 else 200, text="ok")

    sleeps, sleep = _silent_sleep_spy()
    client = PoliteClient(
        transport=httpx2.MockTransport(handler), backoff_base=0.5, min_interval=0.0, sleep=sleep
    )

    assert await client.get_text("https://example.test/x") == "ok"
    assert sleeps == [0.5, 1.0, 2.0]


async def test_polite_client_retries_on_429_then_returns_body() -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(429 if calls["n"] == 1 else 200, text="ok")

    _, sleep = _silent_sleep_spy()
    client = PoliteClient(transport=httpx2.MockTransport(handler), min_interval=0.0, sleep=sleep)

    assert await client.get_text("https://example.test/x") == "ok"
    assert calls["n"] == 2


async def test_polite_client_does_not_wait_when_interval_already_elapsed() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, text="ok")

    sleeps, sleep = _silent_sleep_spy()
    client = PoliteClient(
        transport=httpx2.MockTransport(handler),
        min_interval=1.0,
        sleep=sleep,
        clock=_seq_clock([0.0, 5.0, 5.0]),
    )

    await client.get_text("https://example.test/a")
    await client.get_text("https://example.test/a")

    assert sleeps == []


async def test_polite_client_waits_only_the_remaining_interval() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, text="ok")

    sleeps, sleep = _silent_sleep_spy()
    client = PoliteClient(
        transport=httpx2.MockTransport(handler),
        min_interval=1.5,
        sleep=sleep,
        clock=_seq_clock([0.0, 0.4, 0.4]),
    )

    await client.get_text("https://example.test/a")
    await client.get_text("https://example.test/a")

    assert sleeps == [pytest.approx(1.1)]


async def test_polite_client_does_not_rate_limit_across_distinct_hosts() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, text="ok")

    def frozen_clock() -> float:
        return 1000.0

    sleeps, sleep = _silent_sleep_spy()
    client = PoliteClient(
        transport=httpx2.MockTransport(handler), min_interval=1.5, sleep=sleep, clock=frozen_clock
    )

    await client.get_text("https://a.test/x")
    await client.get_text("https://b.test/y")

    assert sleeps == []


async def test_polite_client_follows_redirects_to_the_final_body() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path == "/old":
            return httpx2.Response(301, headers={"Location": "https://example.test/new"})
        return httpx2.Response(200, text="final")

    _, sleep = _silent_sleep_spy()
    client = PoliteClient(transport=httpx2.MockTransport(handler), min_interval=0.0, sleep=sleep)

    assert await client.get_text("https://example.test/old") == "final"


async def test_polite_client_raises_when_response_exceeds_byte_cap() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, text="x" * 100)

    client = PoliteClient(
        transport=httpx2.MockTransport(handler), min_interval=0.0, max_response_bytes=8
    )

    with pytest.raises(ValueError):
        await client.get_text("https://example.test/x")


async def test_polite_client_throttles_each_retry() -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return httpx2.Response(503 if calls["n"] == 1 else 200, text="ok")

    def frozen_clock() -> float:
        return 1000.0

    sleeps, sleep = _silent_sleep_spy()
    client = PoliteClient(
        transport=httpx2.MockTransport(handler),
        min_interval=1.0,
        backoff_base=0.5,
        sleep=sleep,
        clock=frozen_clock,
    )

    assert await client.get_text("https://example.test/x") == "ok"
    assert calls["n"] == 2
    assert sleeps == [0.5, 1.0]  # backoff after the 503, then the per-host throttle on the retry
