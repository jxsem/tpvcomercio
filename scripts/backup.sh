#!/bin/bash
# Copia de seguridad de la base de datos con pg_dump.
# Uso:  scripts/backup.sh            (con docker compose en marcha)
# Deja el archivo en backups/ (carpeta ignorada por Git: contiene datos reales).
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p backups
FILE="backups/tpvcomercio_$(date +%Y%m%d_%H%M%S).dump"

# Formato custom (-Fc): comprimido y restaurable con pg_restore.
docker compose exec -T postgres pg_dump -U tpv_admin -Fc tpvcomercio > "$FILE"
echo "Backup creado: $FILE"
