#!/bin/bash
# Restaura un backup en una base de datos de PRUEBA (tpvcomercio_restore_test).
# Nunca toca la base real: sirve para comprobar que el backup realmente se restaura.
# Uso:  scripts/restore.sh backups/tpvcomercio_YYYYMMDD_HHMMSS.dump
set -euo pipefail

[ $# -eq 1 ] || { echo "Uso: $0 ARCHIVO.dump" >&2; exit 1; }
cd "$(dirname "$0")/.."
DB=tpvcomercio_restore_test

docker compose exec -T postgres dropdb -U tpv_admin --if-exists "$DB"
docker compose exec -T postgres createdb -U tpv_admin "$DB"
docker compose exec -T postgres pg_restore -U tpv_admin -d "$DB" --no-owner < "$1"

echo "Restaurado en $DB. Comprobación (filas por tabla clave):"
for t in users products sales payments stock_movements audit_logs; do
  printf '%s: ' "$t"
  docker compose exec -T postgres psql -U tpv_admin -d "$DB" -tAc "SELECT count(*) FROM $t"
done
