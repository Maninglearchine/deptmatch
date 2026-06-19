FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# HuggingFace Spaces 비루트 사용자 요구사항
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR /home/user/app

# 의존성 먼저 설치 (레이어 캐시 활용)
COPY --chown=user backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# 앱 코드 복사
COPY --chown=user backend/ backend/
COPY --chown=user dept.xlsx dept.xlsx

# SQLite 데이터 디렉터리 생성
RUN mkdir -p data

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
