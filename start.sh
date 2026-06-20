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

# bge_m3_finetuned: private HF model repo에서 런타임 다운로드
python - <<'PYEOF'
import os
from pathlib import Path
from huggingface_hub import snapshot_download

dest_dir = "/home/user/app/bge_m3_finetuned"
if Path(dest_dir, "model.safetensors").exists():
    print("[OK] bge_m3_finetuned 이미 존재")
else:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("[경고] HF_TOKEN 없음 - 시작 시 base BAAI/bge-m3 사용")
    else:
        print("[다운로드] fine-tuned model (maninglearchine/bge-m3-finetuned-dept)...")
        snapshot_download(
            repo_id="maninglearchine/bge-m3-finetuned-dept",
            repo_type="model",
            local_dir=dest_dir,
            token=token,
        )
        print("[OK] bge_m3_finetuned 준비 완료:", dest_dir)
PYEOF

mkdir -p /home/user/app/data
exec uvicorn backend.main:app --host 0.0.0.0 --port 7860
