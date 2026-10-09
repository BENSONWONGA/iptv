#!/bin/bash
LOG() { echo "== $* =="; }

LOG "1) find correct config option names"
docker exec odk-odoo odoo --help 2>&1 | grep -iE "http|interface|rpc|port|bind" || echo "no matches"

LOG "2) also check full help for interface"
docker exec odk-odoo odoo --help 2>&1 | head -80

LOG "3) get DB password"
PG_PWD=$(docker exec odk-postgres printenv POSTGRES_PASSWORD 2>/dev/null)
echo "PG_PWD:$PG_PWD"
[ -z "$PG_PWD" ] && PG_PWD="odoo@2026"

LOG "4) write config with http_interface"
cat > /tmp/odoo_fixed.conf << EOF
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo
db_host = odk-postgres
db_port = 5432
db_user = odoo
db_password = $PG_PWD
proxy_mode = True
list_db = False
http_interface = 0.0.0.0
http_port = 8069
EOF
docker cp /tmp/odoo_fixed.conf odk-odoo:/etc/odoo/odoo.conf
echo "COPY_EXIT:$?"

LOG "5) restart odoo"
docker restart odk-odoo
echo "waiting 30s..."
sleep 30

LOG "6) check logs for interface binding"
docker logs --tail 20 odk-odoo 2>&1

LOG "7) verify"
code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://127.0.0.1:8069/web/login)
echo "8069:$code"
if [ "$code" = "200" ]; then
  code88=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 http://127.0.0.1:88/web/login)
  echo "88:$code88"
  echo "=== Odoo OK! http://220.162.99.166:88 admin/admin ==="
fi
rm -f /tmp/odoo_fixed.conf
echo "|DONE"
