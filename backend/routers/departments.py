from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Announcement, CrawlLog
from ..schemas import DepartmentOut, CrawlLogOut

router = APIRouter(tags=["departments"])


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Announcement.matched_dept, func.count().label("count"))
        .where(Announcement.matched_dept.is_not(None))
        .group_by(Announcement.matched_dept)
        .order_by(func.count().desc())
    ).all()
    return [DepartmentOut(name=r.matched_dept, count=r.count) for r in rows]


@router.get("/crawl-logs", response_model=list[CrawlLogOut])
def list_crawl_logs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.execute(
        select(CrawlLog)
        .order_by(CrawlLog.started_at.desc())
        .limit(limit)
    ).scalars().all()
    return list(rows)
