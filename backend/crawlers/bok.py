"""
한국은행 (bok.or.kr) 크롤러
listCont.do HTML API 기반 (JS 렌더링 없이 접근 가능한 서버사이드 포함 엔드포인트)
보도자료 / 의결사항
"""
import logging
from datetime import datetime
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_BASE = "https://www.bok.or.kr"

# listCont.do: 전체 페이지 없이 목록 HTML만 반환하는 엔드포인트
_LIST_APIS = {
    "보도자료": (
        f"{_BASE}/portal/singl/newsData/listCont.do"
        "?pageIndex=1&targetDepth=3&menuNo=201263"
        "&syncMenuChekKey=1&depthSubMain=&subMainAt="
        "&searchCnd=1&searchKwd=&depth2=200038&depth3=201263&sort=1&pageUnit=20"
    ),
    "의결사항": (
        f"{_BASE}/portal/singl/newsData/listCont.do"
        "?pageIndex=1&targetDepth=4&menuNo=200761"
        "&syncMenuChekKey=1&depthSubMain=&subMainAt="
        "&searchCnd=1&searchKwd=&depth2=200038&depth3=201154&depth4=200761&sort=1&pageUnit=20"
    ),
}


class BokCrawler(BaseCrawler):
    source_agency = "한국은행"
    agency_class = "bok"

    def get_list(self) -> list[dict]:
        items = []
        for category, url in _LIST_APIS.items():
            try:
                soup = self.fetch(url)
                # 구조: <ul><li>
                #   <span class="i"><span class="t1">보도자료</span></span>
                #   <span class="dataInfo">
                #     <span class="depart"><span class="sr-only">담당부서</span>국제수지팀</span>
                #     <span class="date"><span class="sr-only">등록일</span>2026.06.19</span>
                #   </span>
                #   <div class="set"><a href="/portal/bbs/.../view.do?nttId=...">제목</a></div>
                # </li></ul>
                rows = soup.select("ul li")
                logger.debug("BOK [%s] 행 수: %d (URL: %s)", category, len(rows), url[:80])
                for row in rows:
                    a = row.select_one("div.set a[href]")
                    if not a:
                        continue
                    title = a.get_text(strip=True)
                    if not title:
                        continue
                    href = a.get("href", "")
                    full_url = (_BASE + href) if href.startswith("/") else href

                    # 날짜: span.date에서 sr-only 이후 텍스트
                    date_el = row.select_one("span.date")
                    date_str = ""
                    if date_el:
                        for sr in date_el.select("span.sr-only"):
                            sr.decompose()
                        date_str = date_el.get_text(strip=True)
                    published_at = _parse_date(date_str)

                    # 담당부서
                    dept_el = row.select_one("span.depart")
                    dept_raw = ""
                    if dept_el:
                        for sr in dept_el.select("span.sr-only"):
                            sr.decompose()
                        dept_raw = dept_el.get_text(strip=True)

                    items.append({
                        "category": category,
                        "title": title,
                        "url": full_url,
                        "published_at": published_at,
                        "author_dept_raw": dept_raw,
                    })
            except Exception as exc:
                logger.error("BOK 목록 오류 [%s]: %s", category, exc)
        return items

    def get_detail(self, url: str) -> dict:
        if not url:
            return {}
        try:
            soup = self.fetch(url)
            body_el = soup.select_one(".bbs_view_cont, .view_content, .cont_bx, .view_cont")
            body = body_el.get_text("\n", strip=True)[:3000] if body_el else ""
            return {"body_text": body}
        except Exception as exc:
            logger.debug("BOK 상세 오류 (%s): %s", url, exc)
            return {}


def _parse_date(text: str) -> datetime:
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text.strip()[:10], fmt)
        except ValueError:
            continue
    return datetime.utcnow()


_crawler = BokCrawler()


def crawl() -> list[dict]:
    return _crawler.crawl()
