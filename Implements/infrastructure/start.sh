#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

echo "[infrastructure] starting PostgreSQL..."
docker compose -f docker-compose.postgresql.yml up -d

echo "[infrastructure] waiting for PostgreSQL..."
for _ in $(seq 1 30); do
  health="$(docker inspect --format '{{.State.Health.Status}}' thesis-postgres 2>/dev/null || true)"
  if [[ "$health" == "healthy" ]]; then
    echo "[infrastructure] PostgreSQL is ready at 127.0.0.1:5432"
    exit 0
  fi
  sleep 1
done

echo "[infrastructure] PostgreSQL did not become healthy" >&2
docker compose -f docker-compose.postgresql.yml ps >&2
exit 1
