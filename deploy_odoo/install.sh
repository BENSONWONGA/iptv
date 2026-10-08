#!/bin/bash
# ============================================================
# 奥登科鞋业 ERP · Odoo 20 一键部署脚本（宝塔/Docker 环境）
# 用法：cd 进入本目录后执行  bash install.sh
# 默认动作：起 PostgreSQL + Odoo（含三个自研模块）→ 切 nginx 88 端口 → 验证后删除旧 ERPNext
# 只装 Odoo 不动旧站：SKIP_NGINX=1 bash install.sh
# 保留旧 ERPNext 不删：SKIP_CLEANUP=1 bash install.sh
# ============================================================
set -e
cd "$(dirname "$0")"

DB_NAME=odk_erp
LOG() { echo -e "\n== $* =="; }
DIE() { echo "!! $*" >&2; exit 1; }

# 0) 依赖检查
command -v docker >/dev/null || DIE "未安装 docker"
docker compose version >/dev/null 2>&1 || DIE "docker compose 不可用（老版本请用 docker-compose）"
[ -x "$(command -v openssl)" ] || DIE "缺少 openssl"

# 1) 生成密码与配置
LOG "生成数据库密码与 odoo.conf"
[ -f .env ] || echo "POSTGRES_PASSWORD=odk_$(openssl rand -hex 8)" > .env
source .env
[ -f odoo.conf ] || cat > odoo.conf <<EOF
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
db_host = db
db_port = 5432
db_user = odoo
db_password = ${POSTGRES_PASSWORD}
proxy_mode = True
list_db = False
admin_passwd = $(openssl rand -hex 12)
EOF

# 2) 拉取镜像（odoo:20 不存在则回退 odoo:20.0）
LOG "拉取镜像（国内服务器若超时，请先在宝塔 Docker 里配置镜像加速）"
docker pull odoo:20 2>/dev/null || { docker pull odoo:20.0 && sed -i 's/odoo:20/odoo:20.0/' docker-compose.yml; }
docker pull postgres:16

# 3) 启动数据库并等待就绪
LOG "启动 PostgreSQL"
docker compose up -d db
for i in $(seq 1 30); do
  docker compose exec -T db pg_isready -U odoo >/dev/null 2>&1 && break
  sleep 2
done
docker compose exec -T db pg_isready -U odoo >/dev/null 2>&1 || DIE "PostgreSQL 未就绪"

# 4) 初始化 Odoo 数据库 + 安装三个自研模块（含中文语言包）
LOG "初始化数据库并安装模块（首次约 3-8 分钟）"
docker compose run --rm odoo odoo -d ${DB_NAME} \
  -i odk_scan,odk_subcontract,odk_quality \
  --load-language=zh_CN --without-demo --stop-after-init \
  || DIE "模块安装失败，请把上方日志发给技术支持"

# 5) 启动 Odoo 服务
LOG "启动 Odoo"
docker compose up -d odoo
for i in $(seq 1 30); do
  curl -s -o /dev/null http://127.0.0.1:8069/web/login && break
  sleep 2
done
curl -s -o /dev/null http://127.0.0.1:8069/web/login || DIE "Odoo 启动异常"

# 6) 切换 88 端口 → Odoo；验证通过后删除旧 ERPNext（用户已确认数据可删）
if [ "${SKIP_NGINX}" != "1" ]; then
  LOG "切换 nginx 88 端口 → Odoo"
  if bash switch_nginx.sh; then
    if [ "${SKIP_CLEANUP}" != "1" ]; then
      LOG "删除旧 ERPNext（容器+数据卷，用户已确认）"
      bash cleanup_erpnext.sh
    fi
  else
    echo "!! nginx 切换未成功，保留旧 ERPNext 容器以便回滚" >&2
  fi
fi

LOG "完成"
echo "------------------------------------------------------------"
echo " 访问地址 : http://220.162.99.166:88"
echo " 登录账号 : admin / admin   ←【首次登录后立即修改密码】"
echo " 数据库管理密码(odoo.conf admin_passwd): $(grep admin_passwd odoo.conf | awk '{print $3}')"
echo " 界面改中文：右上角头像 → Preferences → Language 选 简体中文"
echo " 三个模块入口："
echo "   扫码出入库：应用 → 奥登科·扫码出入库"
echo "   委外加工  ：制造 → 委外加工"
echo "   质量管理  ：制造 → 质量管理"
echo " 旧 ERPNext 已按指示删除（nginx 原配置备份路径见上方输出）"
echo "------------------------------------------------------------"
