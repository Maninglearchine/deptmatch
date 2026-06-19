"""
금융위원회 (fsc.go.kr) 크롤러
보도자료 / 고시·공고 / 의결결과
"""
import logging
from datetime import datetime
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_LIST_URLS = {
    "보도자료": "https://www.fsc.go.kr/no010101",
    "고시·공고": "https://www.fsc.go.kr/no010201",
    "의결결과": "https://www.fsc.go.kr/no010301",
}
_BASE = "https://www.fsc.go.kr"


class FscCrawler(BaseCrawler):
    source_agency = "금융위원회"
    agency_class = "fsc"

    def get_list(self) -> list[dict]:
        items = []
        for category, url in _LIST_URLS.items():
            try:
                soup = self.fetch(url)
                # 구조: <ul><li><a href="/no01xxxx/NNNNN?...">제목</a><div>담당부서...</div><div>날짜</div></li>
                for row in soup.select("ul li"):
                    a = None
                    for link in row.select("a[href]"):
                        href = link.get("href", "")
                        # 게시물 링크는 /no01로 시작 (파일 다운로드 /comm/getFile 제외)
                        if href.startswith("/no01") or href.startswith("/no02") or href.startswith("/no03"):
                            a = link
                            break
                    if not a:
                        continue
                    title = a.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue
                    href = a["href"]
                    full_url = (_BASE + href) if href.startswith("/") else href

                    divs = row.select("div")
                    date_str = divs[-1].get_text(strip=True) if divs else ""
                    published_at = _parse_date(date_str)

                    dept_raw = ""
                    for div in divs[:-1]:
                        text = div.get_text(strip=True)
                        if "담당부서" in text:
                            dept_raw = text
                            break

                    items.append({
                        "category": category,
                        "title": title,
                        "url": full_url,
                        "published_at": published_at,
                        "author_dept_raw": dept_raw,
                    })
            except Exception as exc:
                logger.error("FSC 목록 오류 [%s]: %s", category, exc)
        return items

    def get_detail(self, url: str) -> dict:
        if not url:
            return {}
        try:
            soup = self.fetch(url)
            body_el = soup.select_one(".view_content, .board_view_content, .cont_bx, .view_cont")
            body = body_el.get_text("\n", strip=True)[:3000] if body_el else ""

            dept_raw = ""
            for el in soup.select(".info_list li, .detail_info li, .view_info li, .board_info li"):
                text = el.get_text(strip=True)
                if "담당부서" in text or "담당과" in text:
                    dept_raw = text
                    break

            return {"body_text": body, "author_dept_raw": dept_raw}
        except Exception as exc:
            logger.debug("FSC 상세 오류 (%s): %s", url, exc)
            return {}


def _parse_date(text: str) -> datetime:
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text.strip()[:10], fmt)
        except ValueError:
            continue
    return datetime.utcnow()


_crawler = FscCrawler()


def crawl() -> list[dict]:
    return _crawler.crawl()
