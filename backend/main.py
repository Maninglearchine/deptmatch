from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import create_tables
from .routers import announcements, departments
from .services.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    create_tables()
    # 매처를 스케줄러보다 먼저 로드 (스레드풀에서 실행해 이벤트 루프 블록 방지)
    from .services.matcher import get_matcher
    await asyncio.get_event_loop().run_in_executor(None, get_matcher)
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="금융공시 모니터링 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(announcements.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
