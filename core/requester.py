from curl_cffi.requests import AsyncSession
from curl_cffi import Response
from typing import Optional


class Requester:
    def __init__(
        self,
        token: Optional[str] = None,
        cookie: Optional[str] = None,
        proxy: Optional[str] = None,
    ) -> None:
        self.session: AsyncSession | None = None
        self.proxy = proxy
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Origin": "https://eany.io",
            "Referer": "https://eany.io",
        }
        if token:
            self.headers["Accept"] = "application/json, text/plain, */*"
            self.headers["Authorization"] = f"Bearer {token}"
        if cookie:
            self.headers["Cookie"] = cookie
    async def __aenter__(self):
        extra_params = {"timeout": 60, "allow_redirects": True, "http_version": "v2"}
        self.session = AsyncSession(
            impersonate="chrome142",
            headers=self.headers,
            proxy=self.proxy,
            **extra_params
        )
        await self.session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.__aexit__(exc_type, exc, tb)

    async def fetch_get(self, url: str) -> Optional[Response]:
        return await self.session.get(url)