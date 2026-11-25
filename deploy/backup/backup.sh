#!/usr/bin/env bash
# Шифрованная копия базы: pg_dump -> gzip -> age (шифрование публичным ключом) -> внешнее хранилище.
set -euo pipefail

: "${AGE_RECIPIENT:?AGE_RECIPIENT не задан (публичный ключ age)}"
: "${BACKUP_REMOTE:?BACKUP_REMOTE не задан, например backup:bucket/ryadom}"
retention_days="${RETENTION_DAYS:-30}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
file="/tmp/ryadom-${stamp}.sql.gz.age"
trap 'rm -f "${file}"' EXIT

pg_dump --no-owner --no-privileges "${PGDATABASE}" | gzip -9 | age -r "${AGE_RECIPIENT}" -o "${file}"
rclone copyto "${file}" "${BACKUP_REMOTE}/ryadom-${stamp}.sql.gz.age"
# Копии старше срока удаляются (по умолчанию 30 дней): персональные данные не хранятся дольше.
rclone delete "${BACKUP_REMOTE}" --min-age "${retention_days}d" --include "ryadom-*.sql.gz.age"
echo "Резервная копия создана: ryadom-${stamp}.sql.gz.age"
