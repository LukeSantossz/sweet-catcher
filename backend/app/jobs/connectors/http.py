import asyncio
import json
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

import httpx2

DEFAULT_USER_AGENT = "sweet-catcher-jobhunter/0.1 (+https://github.com/lukesantossz/sweet-catcher)"

# Transient conditions worth a retry; everything else (notably 4xx) fails fast.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

# Hard ceiling on a single response body so a malformed or hostile source cannot exhaust memory.
_MAX_RESPONSE_BYTES = 8 * 1024 * 1024


async def _default_sleep(delay: float) -> None:
    await asyncio.sleep(delay)


class PoliteClient:
    """A courteous async HTTP client for the source connectors: an identifiable User-Agent, a
    request timeout, retry with exponential backoff on transient failures, a per-host minimum
    interval between requests, and a hard cap on response body size. The transport, clock, and
    sleep are injectable so the politeness behaviour is exercised without real time or network.

    Throttle state is per instance (per host), so each connector that owns its own client is
    throttled independently — fine while connectors target distinct hosts."""

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        min_interval: float = 1.0,
        max_response_bytes: int = _MAX_RESPONSE_BYTES,
        transport: httpx2.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = _default_sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._min_interval = min_interval
        self._max_response_bytes = max_response_bytes
        self._transport = transport
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: dict[str, float] = {}

    async def get_text(self, url: str, *, params: dict[str, Any] | None = None) -> str:
        return (await self._fetch("GET", url, params=params)).decode("utf-8", errors="replace")

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        return json.loads(await self._fetch("GET", url, params=params))

    async def _fetch(self, method: str, url: str, *, params: dict[str, Any] | None) -> bytes:
        await self._respect_rate_limit(urlsplit(url).netloc)
        async with httpx2.AsyncClient(
            transport=self._transport,
            timeout=self._timeout,
            headers={"User-Agent": self._user_agent},
            follow_redirects=True,
        ) as client:
            attempt = 0
            while True:
                try:
                    async with client.stream(method, url, params=params) as response:
                        retryable = response.status_code in _RETRYABLE_STATUS
                        if not retryable or attempt >= self._max_retries:
                            # 2xx returns; 4xx/5xx (and any non-2xx left after following
                            # redirects) raise. An unread retried response is closed on exit.
                            response.raise_for_status()
                            return await self._read_capped(response)
                except httpx2.TransportError:
                    if attempt >= self._max_retries:
                        raise
                attempt += 1
                await self._sleep(self._backoff_base * (2 ** (attempt - 1)))

    async def _read_capped(self, response: httpx2.Response) -> bytes:
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body += chunk
            if len(body) > self._max_response_bytes:
                raise ValueError(f"response body exceeded the {self._max_response_bytes}-byte cap")
        return bytes(body)

    async def _respect_rate_limit(self, host: str) -> None:
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = self._clock() - last
            if elapsed < self._min_interval:
                await self._sleep(self._min_interval - elapsed)
        self._last_request_at[host] = self._clock()
