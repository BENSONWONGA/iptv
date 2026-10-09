#!/bin/bash
LOG() { echo "== $* =="; }

LOG "1) check port mapping"
docker port odk-odoo 2>&1
docker inspect odk-odoo --format "{{json .NetworkSettings.Ports}}" 2>&1

LOG "2) check container command"
docker inspect odk-odoo --format "{{json .Config.Cmd}}" 2>&1

LOG "3) get DB password"
PG_PWD=$(docker exec odk-postgres printenv POSTGRES_PASSWORD 2>/dev/null)
[ -z "$PG_PWD" ] && PG_PWD="odoo@2026"

LOG "4) write new config with xmlrpc_interface=0.0.0.0"
cat > /tmp/odoo_fixed.conf << EOF
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
db_host = odk-postgres
db_port = 5432
db_user = odoo
db_password = $PG_PWD
proxy_mode = True
list_db = False
xmlrpc = True
xmlrpc_interface = 0.0.0.0
xmlrpc_port = 8069
EOF
docker cp /tmp/odoo_fixed.conf odk-odoo:/etc/odoo/odoo.conf
echo "COPY_EXIT:$?"

LOG "5) show new config"
docker exec odk-odoo cat /etc/odoo/odoo.conf 2>&1

LOG "6) reset PG password"
echo "ALTER USER odoo WITH PASSWORD '$PG_PWD';" > /tmp/_pg.sql
docker exec -i odk-postgres psql -U odoo -d postgres < /tmp/_pg.sql 2>&1
rm -f /tmp/_pg.sql

LOG "7) restart odoo"
docker restart odk-odoo
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
  echo "STILL_FAIL:"
  docker logs --tail 15 odk-odoo 2>&1
fi
rm -f /tmp/odoo_fixed.conf
echo "|DONE"
