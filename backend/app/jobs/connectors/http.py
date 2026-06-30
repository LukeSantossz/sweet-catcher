import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlsplit

import httpx2

DEFAULT_USER_AGENT = "sweet-catcher-jobhunter/0.1 (+https://github.com/lukesantossz/sweet-catcher)"

# Transient conditions worth a retry; everything else (notably 4xx) fails fast.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


async def _default_sleep(delay: float) -> None:
    await asyncio.sleep(delay)


class PoliteClient:
    """A courteous async HTTP client for the source connectors: an identifiable User-Agent, a
    request timeout, retry with exponential backoff on transient failures, and a per-host minimum
    interval between requests. The transport, clock, and sleep are injectable so the politeness
    behaviour can be exercised without real time or network access."""

    def __init__(
        self,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 10.0,
        max_retries: int = 3,
        backoff_base: float = 0.5,
        min_interval: float = 1.0,
        transport: httpx2.AsyncBaseTransport | None = None,
        sleep: Callable[[float], Awaitable[None]] = _default_sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._user_agent = user_agent
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_base = backoff_base
        self._min_interval = min_interval
        self._transport = transport
        self._sleep = sleep
        self._clock = clock
        self._last_request_at: dict[str, float] = {}

    async def get_text(self, url: str, *, params: dict[str, Any] | None = None) -> str:
        response = await self._request("GET", url, params=params)
        return response.text

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None) -> Any:
        response = await self._request("GET", url, params=params)
        return response.json()

    async def _request(
        self, method: str, url: str, *, params: dict[str, Any] | None
    ) -> httpx2.Response:
        await self._respect_rate_limit(urlsplit(url).netloc)
        async with httpx2.AsyncClient(
            transport=self._transport,
            timeout=self._timeout,
            headers={"User-Agent": self._user_agent},
        ) as client:
            attempt = 0
            while True:
                try:
                    response = await client.request(method, url, params=params)
                except httpx2.TransportError:
                    if attempt >= self._max_retries:
                        raise
                else:
                    exhausted = attempt >= self._max_retries
                    if response.status_code not in _RETRYABLE_STATUS or exhausted:
                        # 2xx/3xx pass through; 4xx fails fast; exhausted retryable raises.
                        return response.raise_for_status()
                attempt += 1
                await self._sleep(self._backoff_base * (2 ** (attempt - 1)))

    async def _respect_rate_limit(self, host: str) -> None:
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = self._clock() - last
            if elapsed < self._min_interval:
                await self._sleep(self._min_interval - elapsed)
        self._last_request_at[host] = self._clock()
