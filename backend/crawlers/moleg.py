"""
법제처 (moleg.go.kr) 크롤러
법령해석 사례 목록
"""
import logging
from datetime import datetime
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_BASE = "https://www.moleg.go.kr"
_LIST_URLS = {
    # mid=a10106020000: 법령해석 사례 (table 구조, 정적 HTML)
    "법령해석": f"{_BASE}/menu.es?mid=a10106020000",
}


class MolegCrawler(BaseCrawler):
    source_agency = "법령해석포털"
    agency_class = "moleg"

    def get_list(self) -> list[dict]:
        items = []
        for category, url in _LIST_URLS.items():
            try:
                soup = self.fetch(url)
                # 구조: <table><thead><tr><th>번호/안건번호/안건명/회신일자</th></tr></thead>
                #        <tbody><tr>
                #          <td>8750</td><td>26-0343</td>
                #          <td><a href="/lawinfo/nwLwAnInfo.mo?mid=a10106020000&cs_seq=...">제목</a></td>
                #          <td>2026-06-16</td>
                #        </tr></tbody></table>
                rows = soup.select("table tbody tr")
                logger.debug("Moleg [%s] 행 수: %d (URL: %s)", category, len(rows), url)
                for row in rows:
                    tds = row.select("td")
                    if len(tds) < 4:
                        continue
                    # 제목은 3번째 td의 a 태그
                    a = tds[2].select_one("a[href]") if len(tds) > 2 else None
                    if not a:
                        a = row.select_one("td a[href]")
                    if not a:
                        continue
                    title = a.get_text(strip=True)
                    if not title:
                        continue
                    href = a.get("href", "")
                    if href.startswith("/"):
                        href = _BASE + href
                    elif not href.startswith("http"):
                        continue

                    # 날짜는 마지막 td
                    date_str = tds[-1].get_text(strip=True)
                    published_at = _parse_date(date_str)

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
            body_el = soup.select_one(".view_cont, .law_view, .cont_view, .board_view, .view_content")
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
