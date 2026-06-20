import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from ..config import settings

logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler(timezone="Asia/Seoul")


def _run_crawl(agency_name: str, crawler_fn):
    from ..database import SessionLocal
    from ..models import Announcement, CrawlLog
    from .matcher import get_matcher

    db = SessionLocal()
    log = CrawlLog(source_agency=agency_name, started_at=datetime.utcnow())
    db.add(log)
    db.commit()

    try:
        items = crawler_fn()
        log.items_found = len(items)
        db.commit()  # items_found 즉시 기록

        matcher = get_matcher()
        new_count = 0

        from sqlalchemy import select as sa_select
        from sqlalchemy.exc import IntegrityError

        # 배치 단위 중복 URL 사전 제거 (레이스 컨디션 완화)
        urls = [item["url"] for item in items]
        existing_urls: set[str] = set()
        if urls:
            existing_urls = set(
                db.execute(
                    sa_select(Announcement.url).where(Announcement.url.in_(urls))
                ).scalars().all()
            )

        for item in items:
            if item["url"] in existing_urls:
                continue

            author_dept = item.get('author_dept_raw', '').strip()
            query_text = item['title']
            if author_dept:
                query_text = f"{item['title']}\n담당부서: {author_dept}"
            if item.get('body_text'):
                query_text += f"\n{item['body_text']}"
            result = matcher.predict(query_text)
            ann = Announcement(
                source_agency=item["source_agency"],
                agency_class=item["agency_class"],
                category=item["category"],
                title=item["title"],
                published_at=item["published_at"],
                url=item["url"],
                matched_dept=result["dept"],
                confidence_score=result["confidence"],
                needs_manual_review=result["needs_review"],
                author_dept_raw=item.get("author_dept_raw", ""),
                contact_raw=item.get("contact_raw", ""),
                body_text=item.get("body_text", ""),
            )
            try:
                # savepoint: 아이템 하나 실패해도 세션 유지
                with db.begin_nested():
                    db.add(ann)
                new_count += 1
                existing_urls.add(item["url"])  # 동일 배치 내 중복 방지
            except IntegrityError:
                logger.debug("[%s] 중복 URL 건너뜀: %s", agency_name, item["url"])

        db.commit()
        log.items_new = new_count
        log.status = "success"
        log.finished_at = datetime.utcnow()
        db.commit()
        logger.info("[%s] 완료: 수집 %d건 / 신규 %d건", agency_name, len(items), new_count)

    except Exception as exc:
        db.rollback()
        log.status = "error"
        log.error_msg = str(exc)
        log.finished_at = datetime.utcnow()
        db.commit()
        logger.error("[%s] 오류: %s", agency_name, exc)
    finally:
        db.close()


def start_scheduler():
    from ..crawlers.fsc import crawl as fsc_crawl
    from ..crawlers.fss import crawl as fss_crawl
    from ..crawlers.kofiu import crawl as kofiu_crawl
    from ..crawlers.moleg import crawl as moleg_crawl
    from ..crawlers.bok import crawl as bok_crawl

    jobs = [
        ("금융위원회",     fsc_crawl,   settings.FSC_CRAWL_INTERVAL),
        ("금융감독원",     fss_crawl,   settings.FSS_CRAWL_INTERVAL),
        ("금융정보분석원", kofiu_crawl, settings.KOFIU_CRAWL_INTERVAL),
        ("법령해석포털",   moleg_crawl, settings.MOLEG_CRAWL_INTERVAL),
        ("한국은행",       bok_crawl,   settings.BOK_CRAWL_INTERVAL),
    ]

    now = datetime.now()
    for i, (name, fn, interval) in enumerate(jobs):
        # 주기적 실행
        _scheduler.add_job(
            _run_crawl, "interval", seconds=interval,
            args=[name, fn], id=name,
        )
        # 시작 시 1회 실행 (기관별 30초 간격으로 순차 시작)
        _scheduler.add_job(
            _run_crawl, "date",
            run_date=now + timedelta(seconds=10 + i * 30),
            args=[name, fn], id=f"{name}_init",
        )

    _scheduler.start()
    logger.info("스케줄러 시작 (총 %d개 기관)", len(jobs))


def shutdown_scheduler():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("스케줄러 종료")
