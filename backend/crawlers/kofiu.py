"""
금융정보분석원 KoFIU (kofiu.go.kr) 크롤러
JSON API 기반
보도자료 (seCd=0001) / 고시·공고 (seCd=001)
"""
import logging
from datetime import datetime
from .base import BaseCrawler

logger = logging.getLogger(__name__)

_BASE = "https://www.kofiu.go.kr"

# JSON API 엔드포인트
_APIS = {
    "보도자료": {
        "list_url": f"{_BASE}/cmn/board/selectBoardListFile.do",
        "list_params": {"selScope": "", "subSech": "", "size": "20", "page": "1", "seCd": "0001", "ntcnYardOrdrNo": ""},
        "id_field": "ntcnYardOrdrNo",
        "title_field": "ntcnYardSjNm",
        "date_field": "ntcnYardRgiDt",
        "view_path": "/kor/notification/report_view.do",
        "view_id_param": "ntcnYardOrdrNo",
        "view_se_param": "seCd",
        "view_se_val": "0001",
    },
    "고시·공고": {
        "list_url": f"{_BASE}/cmn/board/selectLawList.do",
        "list_params": {"selScope": "", "subSech": "", "size": "20", "page": "1", "seCd": "001", "ntcnYardOrdrNo": "", "lawordInfoOrdrNo": ""},
        "id_field": "lawordInfoOrdrNo",
        "title_field": "lawordInfoSjNm",
        "date_field": "lawordInfoRgiDt",
        "view_path": "/kor/law/announce_view.do",
        "view_id_param": "lawordInfoOrdrNo",
        "view_se_param": "seCd",
        "view_se_val": "001",
    },
}


class KofiuCrawler(BaseCrawler):
    source_agency = "금융정보분석원"
    agency_class = "kofiu"

    def get_list(self) -> list[dict]:
        items = []
        for category, cfg in _APIS.items():
            try:
                data = self.fetch_json(cfg["list_url"], params=cfg["list_params"])
                records = data if isinstance(data, list) else data.get("result", [])
                logger.debug("KoFIU [%s] 레코드 수: %d", category, len(records))
                for rec in records:
                    seq_id = rec.get(cfg["id_field"], "")
                    title = rec.get(cfg["title_field"], "").strip()
                    date_str = rec.get(cfg["date_field"], "")[:10]
                    if not title or not seq_id:
                        continue
                    view_url = (
                        f"{_BASE}{cfg['view_path']}"
                        f"?{cfg['view_id_param']}={seq_id}"
                        f"&{cfg['view_se_param']}={cfg['view_se_val']}"
                    )
                    published_at = _parse_date(date_str)
                    items.append({
                        "category": category,
                        "title": title,
                        "url": view_url,
                        "published_at": published_at,
                    })
            except Exception as exc:
                logger.error("KoFIU 목록 오류 [%s]: %s", category, exc)
        return items

    def get_detail(self, url: str) -> dict:
        if not url:
            return {}
        try:
            soup = self.fetch(url)
            body_el = soup.select_one(".view_content, .board_view, .cont_view, .bo_view_content")
            body = body_el.get_text("\n", strip=True)[:3000] if body_el else ""
            return {"body_text": body}
        except Exception as exc:
            logger.debug("KoFIU 상세 오류 (%s): %s", url, exc)
            return {}


def _parse_date(text: str) -> datetime:
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(text.strip()[:10], fmt)
        except ValueError:
            continue
    return datetime.utcnow()


_crawler = KofiuCrawler()


def crawl() -> list[dict]:
    return _crawler.crawl()
