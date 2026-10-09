#!/bin/bash
# ============================================================
# Odoo 502 诊断与修复脚本
# 在宝塔【计划任务】中添加 Shell 脚本并运行
# 用途：检查 Odoo 容器状态 → 查看日志 → 重启 → 验证
# ============================================================
set +e
LOG() { echo -e "\n========== $* =========="; }

cd /www/wwwroot/deploy_odoo 2>/dev/null || cd /root/deploy_odoo 2>/dev/null || true

LOG "1) Docker 容器状态"
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>&1

LOG "2) Odoo 容器最近日志（最后 80 行）"
ODOO_C=$(docker ps -a --format '{{.Names}}' 2>/dev/null | grep -i odoo | head -1)
if [ -n "$ODOO_C" ]; then
  echo "容器名: $ODOO_C"
  docker logs --tail 80 "$ODOO_C" 2>&1
else
  echo "!! 未找到 Odoo 容器，可能需要重新部署"
fi

LOG "3) PostgreSQL 容器状态与日志"
DB_C=$(docker ps -a --format '{{.Names}}' 2>/dev/null | grep -iE 'db|postgres' | head -1)
if [ -n "$DB_C" ]; then
  echo "容器名: $DB_C"
  docker logs --tail 20 "$DB_C" 2>&1
  echo "--- pg_isready ---"
  docker exec "$DB_C" pg_isready -U odoo 2>&1
else
  echo "!! 未找到 PostgreSQL 容器"
fi

LOG "4) 重启 Odoo 容器"
if [ -n "$ODOO_C" ]; then
  docker restart "$ODOO_C" 2>&1
  echo "等待 20 秒让 Odoo 启动..."
  sleep 20
fi

LOG "5) 验证 8069 端口"
code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://127.0.0.1:8069/web/login 2>&1)
echo "8069 端口 HTTP 状态码: ${code:-无响应}"

if [ "$code" != "200" ]; then
  LOG "6) 仍然失败，查看重启后日志"
  docker logs --tail 80 "$ODOO_C" 2>&1

  LOG "7) 检查 Odoo 配置文件"
  cat /www/wwwroot/deploy_odoo/odoo.conf 2>/dev/null || cat /root/deploy_odoo/odoo.conf 2>/dev/null || echo "找不到 odoo.conf"

  LOG "8) 检查 .env 密码文件"
  cat /www/wwwroot/deploy_odoo/.env 2>/dev/null || cat /root/deploy_odoo/.env 2>/dev/null || echo "找不到 .env"

  LOG "9) 尝试 docker compose 重启整个服务栈"
  cd /www/wwwroot/deploy_odoo 2>/dev/null || cd /root/deploy_odoo 2>/dev/null
  docker compose down 2>&1
  docker compose up -d db 2>&1
  echo "等待数据库启动..."
  sleep 10
  docker compose up -d odoo 2>&1
  echo "等待 Odoo 启动..."
  sleep 25
  code2=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://127.0.0.1:8069/web/login 2>&1)
  echo "重新启动后 8069 端口 HTTP 状态码: ${code2:-无响应}"

  if [ "$code2" != "200" ]; then
    LOG "10) 仍然失败，输出最终日志供分析"
    docker logs --tail 120 "$ODOO_C" 2>&1
    echo ""
    echo "============================================"
    echo " 修复未成功。请将本页面全部输出截图发给技术支持"
    echo " 或尝试重新部署：cd /www/wwwroot/deploy_odoo && bash install.sh"
    echo "============================================"
  fi
else
  LOG "6) 修复成功！验证 88 端口"
  code88=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://127.0.0.1:88/web/login 2>&1)
  echo "88 端口 HTTP 状态码: ${code88:-无响应}"
  echo ""
  echo "============================================"
  echo " Odoo 已恢复运行！"
  echo " 访问地址: http://220.162.99.166:88"
  echo " 登录账号: admin / admin"
  echo "============================================"
fi

LOG "诊断完成"
