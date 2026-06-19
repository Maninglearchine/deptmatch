from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/announcements.db"
    MODEL_DIR: str = str(BASE_DIR / "bge_m3_finetuned")
    STAGE1_MODEL_DIR: str = str(BASE_DIR / "bge_m3_finetuned")
    RERANKER_DIR: str = str(BASE_DIR / "reranker_model")
    DEPT_EXCEL: str = str(BASE_DIR / "dept.xlsx")

    FSC_CRAWL_INTERVAL: int = 3600
    FSS_CRAWL_INTERVAL: int = 3600
    KOFIU_CRAWL_INTERVAL: int = 3600
    MOLEG_CRAWL_INTERVAL: int = 7200
    BOK_CRAWL_INTERVAL: int = 7200

    CONFIDENCE_AUTO: float = 0.7
    CONFIDENCE_REVIEW: float = 0.4

    model_config = {"env_file": ".env"}


settings = Settings()
