#!/bin/bash
# Se ejecuta UNA vez, al crear el volumen de datos por primera vez.
# Crea el usuario de la aplicación sin superusuario: si alguien explotara una
# vulnerabilidad de la API, no podría crear roles, leer otras bases ni tocar el sistema.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
	CREATE ROLE tpv_app LOGIN PASSWORD '${APP_DB_PASSWORD}'
	  NOSUPERUSER NOCREATEDB NOCREATEROLE;
	ALTER DATABASE ${POSTGRES_DB} OWNER TO tpv_app;
SQL
