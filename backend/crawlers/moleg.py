"""
법령해석포털 / 법제처 (moleg.go.kr) 크롤러
법령해석 / 의견서
"""
import logging
from datetime import datetime
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_BASE = "https://www.moleg.go.kr"
_LIST_URLS = {
    "법령해석": "https://www.moleg.go.kr/lawinfo/lawInterpret/lawInterpretList.mo",
    "법령해석 의견서": "https://www.moleg.go.kr/lawinfo/nwLwAnInfo/nwLwAnInfoList.mo",
}


class MolegCrawler(BaseCrawler):
    source_agency = "법령해석포털"
    agency_class = "moleg"

    def get_list(self) -> list[dict]:
        items = []
        for category, url in _LIST_URLS.items():
            try:
                soup = self.fetch(url)
                for row in soup.select("table tbody tr, ul.list_type li"):
                    a = row.select_one("a[href]")
                    if not a:
                        continue
                    title = a.get_text(strip=True)
                    href = a.get("href", "")
                    if href.startswith("/"):
                        href = _BASE + href
                    elif not href.startswith("http"):
                        continue

                    tds = row.select("td")
                    date_text = tds[-1].get_text(strip=True) if tds else ""
                    published_at = _parse_date(date_text)

                    if title and href:
                        items.append({
                            "category": category,
                            "title": title,
                            "url": href,
                            "published_at": published_at,
                        })
            except Exception as exc:
                logger.error("Moleg 목록 오류 [%s]: %s", category, exc)
        return items

    def get_detail(self, url: str) -> dict:
        if not url:
            return {}
        try:
            soup = self.fetch(url)
            body_el = soup.select_one(".view_cont, .law_view, .cont_view, .board_view")
            body = body_el.get_text("\n", strip=True)[:3000] if body_el else ""
            return {"body_text": body}
        except Exception as exc:
            logger.debug("Moleg 상세 오류 (%s): %s", url, exc)
            return {}


def _parse_date(text: str) -> datetime:
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text.strip()[:10], fmt)
        except ValueError:
            continue
    return datetime.utcnow()


_crawler = MolegCrawler()


def crawl() -> list[dict]:
    return _crawler.crawl()
