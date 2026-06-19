#!/bin/bash
set -e

# dept.xlsx: 빌드 컨텍스트 바이너리 제한 우회 — 런타임에 HF Hub에서 다운로드
python - <<'PYEOF'
import os, shutil
from huggingface_hub import hf_hub_download

dest = "/home/user/app/dept.xlsx"
if os.path.exists(dest):
    print("[OK] dept.xlsx 이미 존재")
else:
    print("[다운로드] dept.xlsx ...")
    path = hf_hub_download(
        repo_id="maninglearchine/deptmatch-api",
        filename="dept.xlsx",
        repo_type="space",
        token=os.environ.get("HF_TOKEN"),
    )
    shutil.copy(path, dest)
    print("[OK] dept.xlsx 준비 완료")
PYEOF

mkdir -p /home/user/app/data
exec uvicorn backend.main:app --host 0.0.0.0 --port 7860
