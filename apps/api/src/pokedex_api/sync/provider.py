from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Protocol, cast

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter


class SourceProvider(Protocol):
    async def get_meta(self) -> dict[str, Any]: ...

    async def list_resources(self, endpoint: str) -> list[dict[str, Any]]: ...

    async def get_resource(self, url: str) -> dict[str, Any]: ...

    async def download(self, url: str) -> tuple[bytes, str | None]: ...


class PokeApiProvider:
    def __init__(
        self,
        base_url: str,
        user_agent: str,
        *,
        concurrency: int = 4,
        page_size: int = 100,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.user_agent = user_agent
        self.page_size = page_size
        self._semaphore = asyncio.Semaphore(concurrency)
        self._client = httpx.AsyncClient(
            headers={"User-Agent": user_agent, "Accept": "application/json"},
            timeout=timeout,
            follow_redirects=True,
        )

    async def __aenter__(self) -> PokeApiProvider:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        wait=wait_exponential_jitter(multiplier=0.5, max=20),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _get(self, url: str) -> httpx.Response:
        full_url = url if url.startswith("http") else f"{self.base_url}/{url.lstrip('/')}"
        async with self._semaphore:
            response = await self._client.get(full_url)
        if response.status_code == 429 or response.status_code >= 500:
            response.raise_for_status()
        response.raise_for_status()
        return response

    async def get_meta(self) -> dict[str, Any]:
        response = await self._get("/meta/")
        return cast(dict[str, Any], response.json())

    async def list_resources(self, endpoint: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        url: str | None = f"/{endpoint.strip('/')}/?limit={self.page_size}&offset=0"
        while url:
            response = await self._get(url)
            payload = response.json()
            results.extend(payload.get("results", []))
            url = payload.get("next")
        return results

    async def get_resource(self, url: str) -> dict[str, Any]:
        response = await self._get(url)
        return cast(dict[str, Any], response.json())

    async def download(self, url: str) -> tuple[bytes, str | None]:
        response = await self._get(url)
        return response.content, response.headers.get("content-type")

    async def iter_resources(
        self, endpoint: str, *, batch_size: int = 40
    ) -> AsyncIterator[dict[str, Any]]:
        summaries = await self.list_resources(endpoint)
        for index in range(0, len(summaries), batch_size):
            batch = summaries[index : index + batch_size]
            resources = await asyncio.gather(
                *(self.get_resource(item["url"]) for item in batch)
            )
            for resource in resources:
                yield resource
