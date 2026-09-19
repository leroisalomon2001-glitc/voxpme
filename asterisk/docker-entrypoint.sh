#!/bin/sh
set -e

# Substitue les variables (${ODBC_DSN_PASSWORD} etc.) dans les fichiers de
# config bootstrap, puis les copie à leur emplacement final dans /etc/asterisk
# et /etc (odbc.ini). Nécessaire car ces fichiers sont montés en volume
# read-only et docker-compose ne substitue pas les variables dans les fichiers
# montés, seulement dans docker-compose.yml lui-même.

for f in /etc/asterisk/bootstrap/*.conf; do
    name=$(basename "$f")
    envsubst < "$f" > "/etc/asterisk/${name}"
done

if [ -f /etc/asterisk/bootstrap/odbc.ini ]; then
    envsubst < /etc/asterisk/bootstrap/odbc.ini > /etc/odbc.ini
fi

exec asterisk -f -vvv
