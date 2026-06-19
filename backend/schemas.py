from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AnnouncementOut(BaseModel):
    id: int
    source_agency: str
    agency_class: str
    category: str
    title: str
    published_at: datetime
    url: str
    matched_dept: Optional[str] = None
    confidence_score: Optional[float] = None
    needs_manual_review: bool
    author_dept_raw: Optional[str] = None
    contact_raw: Optional[str] = None
    body_text: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnouncementList(BaseModel):
    total: int
    page: int
    per_page: int
    items: list[AnnouncementOut]


class RematchResponse(BaseModel):
    id: int
    matched_dept: Optional[str] = None
    confidence_score: Optional[float] = None
    needs_manual_review: bool


class DepartmentOut(BaseModel):
    name: str
    count: int


class CrawlLogOut(BaseModel):
    id: int
    source_agency: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    items_found: int
    items_new: int
    status: str
    error_msg: Optional[str] = None

    model_config = {"from_attributes": True}
