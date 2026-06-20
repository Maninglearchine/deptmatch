"""
금융감독원 (fss.or.kr) 크롤러
보도자료 / 제재공시
"""
import re
import logging
from datetime import datetime
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_BASE = "https://www.fss.or.kr"
_LIST_URLS = {
    "보도자료": "https://www.fss.or.kr/fss/bbs/B0000188/list.do?menuNo=200218",
    "제재공시": "https://www.fss.or.kr/fss/bbs/B0000161/list.do?menuNo=200478",
}
# 날짜 패턴 (YYYY-MM-DD 또는 YYYY.MM.DD)
_DATE_RE = re.compile(r'\d{4}[-./]\d{2}[-./]\d{2}')


class FssCrawler(BaseCrawler):
    source_agency = "금융감독원"
    agency_class = "fss"

    def get_list(self) -> list[dict]:
        items = []
        for category, url in _LIST_URLS.items():
            try:
                soup = self.fetch(url)
                # 보도자료 컬럼: 번호 | 제목(td.title) | 담당부서 | 등록일 | 첨부 | (영상) | 조회수
                # 제재공시 컬럼: 번호 | 금융업종 | 제목(td.title) | 담당부서 | 제재조치요구일 | 첨부 | 조회수
                # → 테이블마다 컬럼 위치가 다르므로 정규식으로 날짜 탐지
                rows = soup.select("table tbody tr")
                logger.debug("FSS [%s] 행 수: %d", category, len(rows))
                for row in rows:
                    tds = row.select("td")
                    if len(tds) < 3:
                        continue
                    a = row.select_one("td.title a, td.subject a")
                    if not a:
                        a = row.select_one("td a[href*='/view.do']")
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

                    # 날짜: 모든 td를 스캔하여 날짜 패턴 탐지
                    date_str = ""
                    dept_raw = ""
                    for td in tds:
                        td_text = td.get_text(strip=True)
                        if not date_str:
                            m = _DATE_RE.search(td_text)
                            if m:
                                date_str = m.group()
                        if "담당부서" in td_text and td.get("class") != ["title"]:
                            dept_raw = td_text.replace("담당부서", "").strip()

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
