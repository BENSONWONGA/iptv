#!/bin/bash
# ============================================================
# 把 nginx 88 端口从 ERPNext 切换为反向代理 Odoo (127.0.0.1:8069)
# 自动备份原配置；恢复方法：cp <备份文件> 回原路径后 reload
# ============================================================
set -e
LOG() { echo -e "\n== $* =="; }
DIE() { echo "!! $*" >&2; exit 1; }

# 1) 定位 88 端口的站点配置（宝塔两种常见路径都找）
CONF=""
for d in /www/server/panel/vhost/nginx /www/server/nginx/conf/vhost; do
  [ -d "$d" ] || continue
  CONF=$(grep -rlE 'listen[[:space:]]+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:)?88([^0-9]|$)' \
        "$d" --include='*.conf' 2>/dev/null | head -1)
  [ -n "$CONF" ] && break
done
[ -n "$CONF" ] || DIE "未在宝塔 vhost 目录找到监听 88 端口的站点配置，请手工处理"

# 2) 备份原配置
BAK="${CONF}.bak.$(date +%Y%m%d%H%M%S)"
cp -a "$CONF" "$BAK"
echo "原配置已备份: $BAK"

# 3) 写入 Odoo 反向代理配置
cat > "$CONF" <<'EOF'
server {
    listen 88;
    listen [::]:88;
    server_name 220.162.99.166 _;

    client_max_body_size 512m;
    proxy_read_timeout 600s;

    location /longpolling {
        proxy_pass http://127.0.0.1:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:8069;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 4) 校验并重载
NGX_BIN=$(command -v nginx || echo /www/server/nginx/sbin/nginx)
"$NGX_BIN" -t || { cp -a "$BAK" "$CONF"; DIE "nginx 配置校验失败，已还原原配置"; }
"$NGX_BIN" -s reload || /etc/init.d/nginx reload

# 5) 验证
sleep 2
code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:88/web/login || true)
[ "$code" = "200" ] && echo "切换成功：http://127.0.0.1:88/web/login → HTTP 200" \
                    || echo "注意：88 端口返回 ${code:-空}，请检查 Odoo 是否在运行"
