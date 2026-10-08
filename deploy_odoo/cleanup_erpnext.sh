#!/bin/bash
# ============================================================
# 删除旧 ERPNext（容器 + 数据卷），释放磁盘
# 由 install.sh 在 Odoo 验证通过后自动调用（用户已确认数据可删）
# 保险开关：手动执行可   bash cleanup_erpnext.sh
# ============================================================
set -u
LOG() { echo -e "\n== $* =="; }

LOG "删除旧 ERPNext 容器"
C=$(docker ps -a --format '{{.Names}}' | grep -iE 'frappe|erpnext|bench' || true)
if [ -n "$C" ]; then
  echo "将删除: $C"
  echo "$C" | xargs -r -n1 docker rm -f
else
  echo "（没有匹配的容器）"
fi

LOG "删除旧 ERPNext 数据卷（MariaDB/站点数据，删除不可恢复）"
V=$(docker volume ls -q | grep -iE 'frappe|erpnext|bench|mariadb' || true)
if [ -n "$V" ]; then
  echo "将删除数据卷: $V"
  echo "$V" | xargs -r -n1 docker volume rm -f
else
  echo "（没有匹配的数据卷）"
fi

LOG "清理完成，当前容器："
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
echo "提示：若 ERPNext 曾用目录挂载（bind mount），站点文件可能残留在磁盘某目录，"
echo "      可在宝塔 文件管理 中手动删除（认准 frappe/erpnext 相关目录）。"
