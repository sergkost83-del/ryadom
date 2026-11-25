#!/usr/bin/env bash
# Откат кода на предыдущую версию (или на указанный тег). Базу не трогает.
# Если новая версия уже изменила схему базы несовместимо, восстановите базу из копии (см. RUNBOOK.md).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="${here}/.."
if [ -n "${1:-}" ]; then
  tag="$1"
else
  tag="$(cat "${here}/.previous_tag")"
fi
compose=(docker compose --env-file .env.prod -f docker-compose.prod.yml)

git -C "${repo}" checkout "tags/${tag}"
cd "${here}"
"${compose[@]}" build
"${compose[@]}" up -d
echo "Откат выполнен на ${tag}"
