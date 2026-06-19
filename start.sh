#!/bin/bash
set -e

# dept.xlsx: private HF Dataset에서 런타임 다운로드 (HF_TOKEN Space secret 필요)
python - <<'PYEOF'
import os, shutil
from huggingface_hub import hf_hub_download

dest = "/home/user/app/dept.xlsx"
if os.path.exists(dest):
    print("[OK] dept.xlsx 이미 존재")
else:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN 환경변수가 없습니다. Space Secrets에 추가해주세요.")
    print("[다운로드] dept.xlsx from HF Dataset (maninglearchine/dept-data)...")
    path = hf_hub_download(
        repo_id="maninglearchine/dept-data",
        filename="dept.xlsx",
        repo_type="dataset",
        token=token,
    )
    shutil.copy(path, dest)
    print("[OK] dept.xlsx 준비 완료:", dest)
PYEOF

mkdir -p /home/user/app/data
exec uvicorn backend.main:app --host 0.0.0.0 --port 7860
