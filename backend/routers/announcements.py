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
