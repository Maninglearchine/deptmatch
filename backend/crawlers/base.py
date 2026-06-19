import logging
from abc import ABC, abstractmethod
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class BaseCrawler(ABC):
    source_agency: str
    agency_class: str
    timeout: int = 20

    def _client(self) -> httpx.Client:
        return httpx.Client(headers=_HEADERS, timeout=self.timeout, verify=False,
                            follow_redirects=True)

    def fetch(self, url: str, **kwargs) -> BeautifulSoup:
        with self._client() as client:
            resp = client.get(url, **kwargs)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")

    def fetch_json(self, url: str, **kwargs) -> dict:
        with self._client() as client:
            resp = client.get(url, **kwargs)
            resp.raise_for_status()
            return resp.json()

    @abstractmethod
    def get_list(self) -> list[dict]:
        ...

    def get_detail(self, url: str) -> dict:
        return {}

    def crawl(self) -> list[dict]:
        items = self.get_list()
        result = []
        for item in items:
            try:
                detail = self.get_detail(item.get("url", ""))
                item.update(detail)
            except Exception as exc:
                logger.debug("상세 오류 (%s): %s", item.get("url"), exc)
            item.setdefault("source_agency", self.source_agency)
            item.setdefault("agency_class", self.agency_class)
            item.setdefault("author_dept_raw", "")
            item.setdefault("contact_raw", "")
            item.setdefault("body_text", "")
            result.append(item)
        return result
