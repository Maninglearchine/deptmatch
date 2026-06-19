"""
금융감독원 (fss.or.kr) 크롤러
보도자료 / 제재공시
"""
import logging
from datetime import datetime
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_BASE = "https://www.fss.or.kr"
_LIST_URLS = {
    "보도자료": "https://www.fss.or.kr/fss/kr/promo/bodobbs_list.jsp",
    "제재공시": "https://www.fss.or.kr/fss/kr/sanction/bbs_list.jsp",
}


class FssCrawler(BaseCrawler):
    source_agency = "금융감독원"
    agency_class = "fss"

    def get_list(self) -> list[dict]:
        items = []
        for category, url in _LIST_URLS.items():
            try:
                soup = self.fetch(url)
                for row in soup.select("table.boardList tbody tr, table tbody tr"):
                    tds = row.select("td")
                    if len(tds) < 2:
                        continue
                    a = row.select_one("td.subject a, td a[href]")
                    if not a:
                        continue
                    title = a.get_text(strip=True)
                    href = a.get("href", "")
                    if href.startswith("/"):
                        href = _BASE + href
                    elif not href.startswith("http"):
                        continue

                    date_el = tds[-1]
                    published_at = _parse_date(date_el.get_text(strip=True))

                    if title and href:
                        items.append({
                            "category": category,
                            "title": title,
                            "url": href,
                            "published_at": published_at,
                        })
            except Exception as exc:
                logger.error("FSS 목록 오류 [%s]: %s", category, exc)
        return items

    def get_detail(self, url: str) -> dict:
        if not url:
            return {}
        try:
            soup = self.fetch(url)
            body_el = soup.select_one(".board_view, .viewContent, .cont_view")
            body = body_el.get_text("\n", strip=True)[:3000] if body_el else ""
            return {"body_text": body}
        except Exception as exc:
            logger.debug("FSS 상세 오류 (%s): %s", url, exc)
            return {}


def _parse_date(text: str) -> datetime:
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text.strip()[:10], fmt)
        except ValueError:
            continue
    return datetime.utcnow()


_crawler = FssCrawler()


def crawl() -> list[dict]:
    return _crawler.crawl()
