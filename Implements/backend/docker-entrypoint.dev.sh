#!/bin/sh
set -e
# Bind-mount overlays /app. Reinstall from requirements.txt on every start.
echo "[backend] installing Python dependencies..."
pip install --no-cache-dir -r /app/requirements.txt
exec "$@"
