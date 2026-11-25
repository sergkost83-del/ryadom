#!/usr/bin/env bash
# Учение по восстановлению: расшифровывает копию во временную базу, проверяет, что данные читаются, и удаляет её.
# Запускать раз в месяц: копия, которую не проверяли, не считается копией.
set -euo pipefail

backup_file="${1:?Использование: restore-drill.sh <файл.sql.gz.age>}"
: "${AGE_IDENTITY_FILE:?AGE_IDENTITY_FILE не задан (путь к приватному ключу age)}"
drill_db="ryadom_drill_$(date -u +%s)"
trap 'dropdb --if-exists "${drill_db}" >/dev/null 2>&1 || true' EXIT

createdb "${drill_db}"
age -d -i "${AGE_IDENTITY_FILE}" "${backup_file}" | gunzip | psql -v ON_ERROR_STOP=1 --quiet "${drill_db}" > /dev/null
tables="$(psql -At "${drill_db}" -c "select count(*) from information_schema.tables where table_schema = 'public'")"
users="$(psql -At "${drill_db}" -c "select count(*) from identity_user")"
echo "Копия читается: таблиц ${tables}, пользователей ${users}"
test "${tables}" -gt 10
