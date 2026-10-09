#!/bin/bash
# ============================================================
# 奥登科 ERP · Odoo 20 一键初始化业务数据库脚本
# 在宝塔【终端】中执行： bash /www/wwwroot/deploy_odoo/init_db.sh
#   (路径按你的实际部署位置替换)
# 用途：
#   1. 创建空 odoo 数据库
#   2. 用 odoo-cli 装入: base/sale/stock/purchase/mrp
#      + 自研三模块(扫码出入库/委外加工/质量管理)
#   3. 加载中文语言
#   4. 写最终 odoo.conf (db_name=odoo, 跳过库选择页)
#   5. 重启 Odoo，验证 8069 / 88 端口
# 耗时 3~5 分钟，期间不要中断
# ============================================================
set -u
LOG()  { echo -e "\n========== $* =========="; }
OK()   { echo "  [OK] $*"; }
WARN() { echo "  [!]  $*"; }
DIE()  { echo "  [X]  $*" >&2; exit 1; }

LOG "0) 前置检查：容器名 / 路径"
# 自动找 Odoo / Postgres 容器名
ODOO_C=$(docker ps --format '{{.Names}} {{.Image}}' 2>/dev/null \
         | grep -iE 'odoo' | grep -ivE 'postgres|pg' | head -1 | awk '{print $1}')
DB_C=$(docker ps --format '{{.Names}} {{.Image}}' 2>/dev/null \
       | grep -iE 'postgres|pg' | head -1 | awk '{print $1}')
[ -z "$ODOO_C" ] && DIE "未发现 Odoo 容器，请先部署 install.sh"
[ -z "$DB_C" ]   && DIE "未发现 Postgres 容器"
OK "Odoo 容器    = $ODOO_C"
OK "PG   容器    = $DB_C"

# 找挂载的 extra-addons 路径（容器内）
EXTRA_DIR=$(docker inspect "$ODOO_C" --format '{{range .Mounts}}{{if eq .Destination "/mnt/extra-addons"}}{{.Source}}{{end}}{{end}}' 2>/dev/null)
if [ -n "$EXTRA_DIR" ]; then
  OK "自研模块挂载 = $EXTRA_DIR → /mnt/extra-addons"
else
  WARN "未发现 /mnt/extra-addons 挂载，自研模块可能装不上"
fi

LOG "1) 检查自研模块是否在容器内可见"
for m in odk_scan odk_subcontract odk_quality; do
  if docker exec "$ODOO_C" test -f "/mnt/extra-addons/$m/__manifest__.py" 2>/dev/null; then
    OK "$m 可见"
  else
    WARN "$m 不在容器内 /mnt/extra-addons/$m"
    WARN "  → 如果 install.sh 已挂载目录但 init 失败，请把 deploy_odoo/addons/* 复制到 $EXTRA_DIR 后重跑"
  fi
done

LOG "2) 取 Postgres 真实密码"
PG_PWD=$(docker exec "$DB_C" printenv POSTGRES_PASSWORD 2>/dev/null)
[ -z "$PG_PWD" ] && PG_PWD="odoo@2026"
OK "PG_PWD 长度 = ${#PG_PWD}"

LOG "3) 检查 odoo 业务数据库是否已存在"
DB_EXISTS=$(docker exec "$DB_C" psql -U odoo -d postgres -tAc \
            "SELECT 1 FROM pg_database WHERE datname='odoo'" 2>/dev/null)
echo "  DB_EXISTS = ${DB_EXISTS:-空}"

LOG "4) 若库已存在但未初始化 → 删除重建（保留已初始化的库不动）"
if [ "$DB_EXISTS" = "1" ]; then
  # 检查 ir_module_module 表是否已存在（已 init 标志）
  HAS_MOD=$(docker exec "$DB_C" psql -U odoo -d odoo -tAc \
            "SELECT count(*) FROM information_schema.tables WHERE table_name='ir_module_module'" 2>/dev/null)
  echo "  ir_module_module 表存在 = ${HAS_MOD:-0}"
  if [ "${HAS_MOD:-0}" = "0" ]; then
    WARN "odoo 库存在但未初始化，删除重建"
    docker exec "$DB_C" psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS odoo" 2>&1
    DB_EXISTS=""
  else
    OK "odoo 库已初始化，跳过 create 步骤，直接进入 init modules"
  fi
fi

if [ "$DB_EXISTS" != "1" ]; then
  OK "创建空 odoo 数据库"
  docker exec "$DB_C" psql -U odoo -d postgres -c "CREATE DATABASE odoo OWNER odoo ENCODING 'UTF8' TEMPLATE template0" 2>&1
fi

LOG "5) 写一份临时 conf（仅用于本次 init，含正确 addons_path + 密码）"
cat > /tmp/odoo_init.conf << EOF
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
db_host = $DB_C
db_port = 5432
db_user = odoo
db_password = $PG_PWD
list_db = False
db_name = odoo
http_interface = 0.0.0.0
http_port = 8069
EOF
docker cp /tmp/odoo_init.conf "$ODOO_C":/etc/odoo/odoo.conf
OK "临时 conf 已写入容器 /etc/odoo/odoo.conf"
rm -f /tmp/odoo_init.conf

LOG "6) 初始化业务模块（耗时 3~5 分钟，期间无输出属正常）"
docker exec -i "$ODOO_C" odoo -c /etc/odoo/odoo.conf -d odoo \
  -i base,sale_management,stock,purchase,mrp,account,odk_scan,odk_subcontract,odk_quality \
  --stop-after-init --without-demo=all --load-language=zh_CN 2>&1 | tail -60
INIT_RC=${PIPESTATUS[0]}
echo "  init 退出码 = $INIT_RC"
[ "$INIT_RC" != "0" ] && DIE "init 失败，请把上面 60 行日志发给技术支持"

LOG "7) 设置 admin 密码为 admin（若未设）"
docker exec "$DB_C" psql -U odoo -d odoo -c \
  "UPDATE res_users SET password='admin' WHERE login='admin'" 2>&1 | tail -3

LOG "8) 重启 Odoo 加载新库"
docker restart "$ODOO_C"
echo "  等待 35 秒..."
sleep 35

LOG "9) 验证 8069 / 88 登录页"
code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 -L http://127.0.0.1:8069/web/login)
echo "  8069 = $code"
code88=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 -L http://127.0.0.1:88/web/login)
echo "  88   = $code88"

LOG "10) 用 JSON-RPC 实际登录验证"
LOGIN_RESULT=$(curl -s --connect-timeout 10 -X POST -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"call","params":{"service":"common","method":"authenticate","args":["odoo","admin","admin",{}]}}' \
  http://127.0.0.1:88/jsonrpc 2>&1)
echo "  login 返回 = $LOGIN_RESULT"

if [ "$code88" = "200" ]; then
  echo ""
  echo "============================================="
  echo "  ✅ Odoo 业务库初始化完成"
  echo "  访问: http://220.162.99.166:88"
  echo "  账号: admin / admin"
  echo "  已装: base + 销售 + 库存 + 采购 + MRP + 会计"
  echo "       + 扫码出入库(odk_scan)"
  echo "       + 委外加工(odk_subcontract)"
  echo "       + 质量管理(odk_quality)"
  echo "  语言: 中文"
  echo "============================================="
else
  echo ""
  echo "  [X] 验证未通过，下面是最近日志："
  docker logs --tail 30 "$ODOO_C" 2>&1
fi
echo "|DONE"
