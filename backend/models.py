from datetime import datetime
from sqlalchemy import String, Float, Boolean, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_agency: Mapped[str] = mapped_column(String(50), index=True)
    agency_class: Mapped[str] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(500))
    published_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)

    matched_dept: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_manual_review: Mapped[bool] = mapped_column(Boolean, default=False)

    author_dept_raw: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_raw: Mapped[str | None] = mapped_column(String(200), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CrawlLog(Base):
    __tablename__ = "crawl_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_agency: Mapped[str] = mapped_column(String(50), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    items_found: Mapped[int] = mapped_column(Integer, default=0)
    items_new: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
