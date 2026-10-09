#!/bin/bash
# Odoo 502 fix: sync odoo.conf password <-> PostgreSQL actual password
LOG() { echo "== $* =="; }

LOG "1) containers"
ODOO_C=$(docker ps -a --format "{{.Names}} {{.Image}}" | grep -i odoo | grep -iv postgres | head -1 | cut -d" " -f1)
DB_C=$(docker ps -a --format "{{.Names}} {{.Image}}" | grep -i postgres | head -1 | cut -d" " -f1)
echo "Odoo:$ODOO_C DB:$DB_C"
if [ -z "$ODOO_C" ] || [ -z "$DB_C" ]; then echo "FAIL: no containers"; exit 1; fi

LOG "2) get DB env password"
PG_PWD=$(docker exec "$DB_C" printenv POSTGRES_PASSWORD 2>/dev/null)
echo "DB_ENV_PWD:$PG_PWD"

LOG "3) get current odoo.conf password from container"
CUR_PWD=$(docker exec "$ODOO_C" grep "^db_password" /etc/odoo/odoo.conf 2>/dev/null | sed "s/.*= *//")
echo "CUR_PWD:$CUR_PWD"

LOG "4) find host odoo.conf path via docker inspect"
CONF=$(docker inspect "$ODOO_C" --format "{{range .Mounts}}{{if eq .Destination \"/etc/odoo/odoo.conf\"}}{{.Source}}{{end}}{{end}}" 2>/dev/null)
echo "CONF_DOCKER:$CONF"
if [ -z "$CONF" ]; then
  CONF=$(find / -maxdepth 6 -name odoo.conf -not -path "*/proc/*" -not -path "*/var/lib/docker/*" 2>/dev/null | head -1)
  echo "CONF_FIND:$CONF"
fi

LOG "5) sync"
if [ -z "$PG_PWD" ]; then echo "FAIL: no DB pwd"; exit 1; fi

if [ -n "$CONF" ] && [ -f "$CONF" ]; then
  if [ "$CUR_PWD" != "$PG_PWD" ]; then
    sed -i "s/^db_password.*/db_password = $PG_PWD/" "$CONF"
    echo "CONF_UPDATED: $CONF"
  else
    echo "CONF_ALREADY_MATCH"
  fi
else
  echo "WARN: host conf not found, will recreate inside container"
  docker exec -u root "$ODOO_C" sh -c "echo 'db_password = $PG_PWD' >> /etc/odoo/odoo.conf.tmp && cat /etc/odoo/odoo.conf | grep -v '^db_password' > /etc/odoo/odoo.conf.tmp && echo 'db_password = $PG_PWD' >> /etc/odoo/odoo.conf.tmp && cp /etc/odoo/odoo.conf.tmp /etc/odoo/odoo.conf" 2>/dev/null
  echo "CONTAINER_CONF_UPDATED"
fi

LOG "6) reset PG password via SQL (belt-and-suspenders)"
echo "ALTER USER odoo WITH PASSWORD '$PG_PWD';" > /tmp/_pg_reset.sql
docker exec -i "$DB_C" psql -U odoo -d postgres < /tmp/_pg_reset.sql 2>&1
rm -f /tmp/_pg_reset.sql

LOG "7) restart odoo"
docker restart "$ODOO_C"
echo "waiting 30s..."
sleep 30

LOG "8) verify"
code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://127.0.0.1:8069/web/login)
echo "8069:$code"
if [ "$code" = "200" ]; then
  code88=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://127.0.0.1:88/web/login)
  echo "88:$code88"
  echo "=== Odoo OK! http://220.162.99.166:88 admin/admin ==="
else
  echo "STILL_FAIL, logs:"
  docker logs --tail 15 "$ODOO_C" 2>&1
fi
echo "|DONE"
