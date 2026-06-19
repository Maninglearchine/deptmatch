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
    "보도자료": "https://www.fss.or.kr/fss/bbs/B0000188/list.do?menuNo=200218",
    "제재공시": "https://www.fss.or.kr/fss/bbs/B0000161/list.do?menuNo=200478",
}


class FssCrawler(BaseCrawler):
    source_agency = "금융감독원"
    agency_class = "fss"

    def get_list(self) -> list[dict]:
        items = []
        for category, url in _LIST_URLS.items():
            try:
                soup = self.fetch(url)
                # 구조: <table><tbody><tr>
                #   <td class="num no">번호</td>
                #   <td class="title"><a href="/fss/bbs/.../view.do?nttId=...">제목</a></td>
                #   <td><span class="only-m">담당부서</span>부서명</td>
                #   <td><span class="only-m">등록일</span>2026-06-19</td>
                # </tr></tbody></table>
                rows = soup.select("table tbody tr")
                logger.debug("FSS [%s] 행 수: %d (URL: %s)", category, len(rows), url)
                for row in rows:
                    tds = row.select("td")
                    if len(tds) < 3:
                        continue
                    a = row.select_one("td.title a, td.subject a")
                    if not a:
                        a = row.select_one("td a[href*='/view.do'], td a[href*='/bbs/']")
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

                    # td[2]: 담당부서 (span.only-m 제거 후 텍스트)
                    dept_raw = ""
                    if len(tds) > 2:
                        dept_raw = tds[2].get_text(strip=True).replace("담당부서", "").strip()

                    # td[3]: 등록일
                    date_str = ""
                    if len(tds) > 3:
                        date_str = tds[3].get_text(strip=True).replace("등록일", "").strip()

                    published_at = _parse_date(date_str)

                    items.append({
                        "category": category,
                        "title": title,
                        "url": href,
                        "published_at": published_at,
                        "author_dept_raw": dept_raw,
                    })
            except Exception as exc:
                logger.error("FSS 목록 오류 [%s]: %s", category, exc)
        return items

    def get_detail(self, url: str) -> dict:
        if not url:
            return {}
        try:
            soup = self.fetch(url)
            body_el = soup.select_one(".board_view, .viewContent, .cont_view, .view_content")
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
