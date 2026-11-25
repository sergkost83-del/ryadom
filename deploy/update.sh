#!/usr/bin/env bash
# Обновление до версии (тега Git): копия базы -> сборка -> миграции -> перезапуск. Запускать на сервере.
set -euo pipefail

tag="${1:?Использование: update.sh <тег>, например v0.9.0}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="${here}/.."
compose=(docker compose --env-file .env.prod -f docker-compose.prod.yml)

previous="$(git -C "${repo}" describe --tags --always)"
echo "${previous}" > "${here}/.previous_tag"
git -C "${repo}" fetch --tags --prune
git -C "${repo}" checkout "tags/${tag}"

cd "${here}"
"${compose[@]}" build
"${compose[@]}" --profile tools run --rm backup
"${compose[@]}" run --rm backend python manage.py migrate --noinput
"${compose[@]}" run --rm backend python manage.py setup_roles
"${compose[@]}" up -d
echo "Обновлено: ${previous} -> ${tag}. Проверьте https://ВАШ_ДОМЕН/api/v1/health/"
