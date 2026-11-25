#!/usr/bin/env bash
# Восстановление базы из шифрованной копии. ПЕРЕЗАПИШЕТ все данные в базе PGDATABASE.
# Перед запуском остановите backend. Приватный ключ age хранится только у администратора, не на сервере.
set -euo pipefail

backup_file="${1:?Использование: restore.sh <файл.sql.gz.age>}"
: "${AGE_IDENTITY_FILE:?AGE_IDENTITY_FILE не задан (путь к приватному ключу age)}"
if [ "${CONFIRM_RESTORE:-}" != "yes" ]; then
  echo "Остановлено: данные в базе будут перезаписаны. Повторите с CONFIRM_RESTORE=yes" >&2
  exit 2
fi

dropdb --if-exists "${PGDATABASE}"
createdb "${PGDATABASE}"
age -d -i "${AGE_IDENTITY_FILE}" "${backup_file}" | gunzip | psql -v ON_ERROR_STOP=1 --quiet "${PGDATABASE}"
echo "База восстановлена из ${backup_file}"
