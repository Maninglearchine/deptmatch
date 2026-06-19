from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Announcement
from ..schemas import AnnouncementList, AnnouncementOut, RematchResponse
from ..services.matcher import get_matcher

router = APIRouter(tags=["announcements"])

_RANGE_DAYS = {"D": 1, "W": 7, "M": 30}


@router.get("/crawl/logs")
def crawl_logs(limit: int = 20, db: Session = Depends(get_db)):
    """최근 크롤링 실행 이력 조회."""
    from ..models import CrawlLog
    from sqlalchemy import select
    logs = db.execute(
        select(CrawlLog).order_by(CrawlLog.started_at.desc()).limit(limit)
    ).scalars().all()
    return [
        {
            "agency": l.source_agency,
            "started_at": l.started_at.isoformat() if l.started_at else None,
            "finished_at": l.finished_at.isoformat() if l.finished_at else None,
            "items_found": l.items_found,
            "items_new": l.items_new,
            "status": l.status,
            "error_msg": l.error_msg,
        }
        for l in logs
    ]


@router.get("/debug/fetch")
def debug_fetch(url: str):
    """크롤러가 실제로 받는 HTML 앞부분을 반환 (배포 환경 셀렉터 디버그용)."""
    import httpx
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        r = httpx.get(url, headers=headers, timeout=20, verify=False, follow_redirects=True)
        html = r.text
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        tables = [{"class": t.get("class", []), "rows": len(t.select("tbody tr"))} for t in soup.select("table")[:5]]
        uls = [{"class": u.get("class", []), "lis": len(u.select("li"))} for u in soup.select("ul")[:5]]
        first_a = soup.select_one("a[href]")
        return {
            "status_code": r.status_code,
            "html_len": len(html),
            "html_preview": html[:1500],
            "tables": tables,
            "uls": uls,
            "first_a": {"href": first_a.get("href"), "text": first_a.get_text()[:50]} if first_a else None,
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/crawl")
def trigger_crawl():
    """모든 기관 크롤러 즉시 수동 실행."""
    import threading
    from ..services.scheduler import _run_crawl
    from ..crawlers.fsc import crawl as fsc_crawl
    from ..crawlers.fss import crawl as fss_crawl
    from ..crawlers.kofiu import crawl as kofiu_crawl
    from ..crawlers.moleg import crawl as moleg_crawl
    from ..crawlers.bok import crawl as bok_crawl

    jobs = [
        ("금융위원회",     fsc_crawl),
        ("금융감독원",     fss_crawl),
        ("금융정보분석원", kofiu_crawl),
        ("법령해석포털",   moleg_crawl),
        ("한국은행",       bok_crawl),
    ]
    for name, fn in jobs:
        threading.Thread(target=_run_crawl, args=[name, fn], daemon=True).start()

    return {"status": "started", "agencies": [name for name, _ in jobs]}


@router.get("/announcements", response_model=AnnouncementList)
def list_announcements(
    source_agency: Optional[str] = None,
    category: Optional[str] = None,
    dept: Optional[str] = None,
    range: str = "M",
    min_confidence: float = 0.0,
    review_only: bool = False,
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
):
    q = select(Announcement)

    if range in _RANGE_DAYS:
        since = datetime.utcnow() - timedelta(days=_RANGE_DAYS[range])
        q = q.where(Announcement.published_at >= since)
    if source_agency:
        q = q.where(Announcement.source_agency == source_agency)
    if category:
        q = q.where(Announcement.category == category)
    if dept:
        q = q.where(Announcement.matched_dept.contains(dept))
    if min_confidence > 0:
        q = q.where(Announcement.confidence_score >= min_confidence)
    if review_only:
        q = q.where(Announcement.needs_manual_review == True)  # noqa: E712

    q = q.order_by(Announcement.published_at.desc())

    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    items = db.execute(q.offset((page - 1) * per_page).limit(per_page)).scalars().all()

    return AnnouncementList(total=total, page=page, per_page=per_page, items=list(items))


@router.get("/announcements/{id}", response_model=AnnouncementOut)
def get_announcement(id: int, db: Session = Depends(get_db)):
    item = db.get(Announcement, id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item


@router.post("/announcements/{id}/rematch", response_model=RematchResponse)
def rematch(id: int, db: Session = Depends(get_db)):
    item = db.get(Announcement, id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")

    matcher = get_matcher()
    result = matcher.predict(f"{item.title} {item.body_text or ''}")

    item.matched_dept = result["dept"]
    item.confidence_score = result["confidence"]
    item.needs_manual_review = result["needs_review"]
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    return RematchResponse(
        id=item.id,
        matched_dept=item.matched_dept,
        confidence_score=item.confidence_score,
        needs_manual_review=item.needs_manual_review,
    )
