#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "[backend] creating .venv..."
  python3 -m venv .venv
fi

echo "[backend] installing dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "[backend] starting http://127.0.0.1:8000"
exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
