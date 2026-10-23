from typing import Any

import httpx
from markdownify import markdownify

from wikitui.config import Config


class WikiClient:
    """Minimal async client for the BookStack REST API."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._http = httpx.AsyncClient(
            base_url=f"{config.url}/api",
            headers=config.auth_header,
            timeout=15,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get(self, path: str, **params: Any) -> Any:
        r = await self._http.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def _list(self, path: str, **params: Any) -> list[dict]:
        items: list[dict] = []
        while True:
            body = await self._get(path, count=100, offset=len(items), **params)
            items.extend(body["data"])
            if len(items) >= body["total"] or not body["data"]:
                return items

    async def books(self) -> list[dict]:
        return await self._list("/books", sort="+name")

    async def book(self, book_id: int) -> dict:
        return await self._get(f"/books/{book_id}")

    async def search(self, query: str) -> list[dict]:
        body = await self._get("/search", query=query, count=50)
        return body["data"]

    async def page_by_slug(self, book_slug: str, page_slug: str) -> dict | None:
        pages = await self._get("/pages", **{"filter[slug]": page_slug, "count": 20})
        books = {}
        for p in pages["data"]:
            if p.get("book_slug") == book_slug:
                return p
            books[p["book_id"]] = p
        return next(iter(books.values()), None)

    async def page_markdown(self, page_id: int) -> tuple[str, str]:
        """Return (title, markdown) for a page, converting HTML if it has no Markdown source."""
        page = await self._get(f"/pages/{page_id}")
        text = page.get("markdown") or markdownify(page.get("html", ""), heading_style="ATX")
        return page["name"], text

    def page_url(self, page: dict) -> str:
        if page.get("book_slug") and page.get("slug"):
            return f"{self.config.url}/books/{page['book_slug']}/page/{page['slug']}"
        return f"{self.config.url}/link/{page['id']}"
