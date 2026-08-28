#!/bin/sh
set -e
# Bind-mount + named volume hide the image node_modules. Reinstall from
# package-lock.json on every start so new deps (e.g. Tailwind) are never stale.
echo "[frontend] installing npm dependencies..."
npm ci
exec "$@"
