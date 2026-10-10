#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v2 全能安装包：不依赖旧目录，全新机器/残留机器均可一键装好
打包 deploy_odoo 全套（compose+安装脚本+8模块）→ 生成自适应脚本 → 上传附件"""
import base64
import io
import json
import os
import tarfile
import urllib.request

ROOT = "/workspace/deploy_odoo"
TGZ = "/workspace/odk_full_stack.tar.gz"
SH = "/workspace/odk_install_all.sh"
URL = 'http://220.162.99.166:88'
DB, USER, PWD = 'odk_erp', 'admin', 'admin'

EXCLUDES = ['deploy_odoo/odoo.conf', 'deploy_odoo/.env',
            'deploy_odoo/cleanup_erpnext.sh', 'deploy_odoo/init_db.sh',
            'deploy_odoo/fix_pwd', 'deploy_odoo/diagnose_and_fix.sh']

# ---------- 1) 打包（只带核心文件 + addons 8 模块） ----------
def skip(t):
    b = os.path.basename(t.name)
    full = t.name
    if b == "__pycache__" or b.endswith(".pyc"):
        return None
    for e in EXCLUDES:
        if full == e or full.startswith(e):
            return None
    return t

with tarfile.open(TGZ, "w:gz") as tf:
    tf.add(ROOT, arcname="deploy_odoo", filter=skip)
names = tarfile.open(TGZ).getnames()
must = ['deploy_odoo/docker-compose.yml', 'deploy_odoo/install.sh',
        'deploy_odoo/switch_nginx.sh', 'deploy_odoo/addons/odk_dispatch/__manifest__.py',
        'deploy_odoo/addons/odk_tech/__manifest__.py']
for m in must:
    assert m in names, '缺少 %s' % m
mods = sorted({n.split('/')[2] for n in names
               if n.startswith('deploy_odoo/addons/') and n.count('/') >= 2})
print('打包: %.1f KB | 文件 %d | 模块 %d 个: %s'
      % (os.path.getsize(TGZ) / 1024, len(names), len(mods), mods))
assert len(mods) == 8
with tarfile.open(TGZ) as tf:
    m = tf.extractfile('deploy_odoo/addons/odk_dispatch/__manifest__.py').read().decode()
    assert '"version": "20.0.2.0.2"' in m and '"depends": ["odk_wms", "mrp", "web"]' in m
    assert 'report_file' not in \
        tf.extractfile('deploy_odoo/addons/odk_dispatch/views/barcode_views.xml').read().decode()
print('校验 OK: odk_dispatch v20.0.2.0.2 修复版在内')

# ---------- 2) 生成自适应安装脚本 ----------
b64 = base64.b64encode(open(TGZ, 'rb').read()).decode()
script = """#!/bin/bash
# ============================================================
# 奥登科 ERP · Odoo 20 一键全新安装（全能版 v2）
# 适配场景：服务器上无论有没有旧部署目录，均可从零装好
# 动作：备份旧库(如有) → 停旧栈清旧卷 → 全新目录+配置 → 初始化 11 应用 → 验证
# 全程约 5-10 分钟
# ============================================================
set -e
BASE=/www/wwwroot
DST=$BASE/deploy_odoo

echo '== 0/7 环境检查 =='
command -v docker >/dev/null || { echo '!! 未安装 docker，请先在宝塔安装 Docker'; exit 1; }
docker compose version >/dev/null 2>&1 || { echo '!! docker compose 不可用'; exit 1; }
echo 'docker OK'

echo '== 1/7 拉取镜像（已存在则秒过） =='
docker pull odoo:20 >/dev/null 2>&1 || docker pull odoo:20.0 >/dev/null 2>&1
docker pull postgres:16 >/dev/null 2>&1
echo '镜像就绪'

echo '== 2/7 备份旧数据库（如能找到旧部署） =='
OLD=""
for d in $DST /root/deploy_odoo; do
  [ -d "$d" ] && OLD="$d" && break
done
if [ -z "$OLD" ]; then
  OC=$(docker ps -a --format '{{.Names}}' | grep -i odoo | head -1)
  [ -n "$OC" ] && OLD=$(docker inspect --format \\
    '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' "$OC" 2>/dev/null || true)
  [ -n "$OLD" ] && [ -d "$OLD" ] || OLD=""
fi
BK=""
if [ -n "$OLD" ] && [ -f "$OLD/docker-compose.yml" ]; then
  echo "发现旧部署: $OLD"
  BK=$BASE/backup_odk_erp_$(date +%Y%m%d_%H%M%S).sql
  (cd "$OLD" && docker compose exec -T db pg_dump -U odoo odk_erp > "$BK" 2>/dev/null \\
    && echo "备份完成: $BK ($(du -h "$BK" | cut -f1))") || { echo '备份失败（继续全新安装）'; BK=""; }
else
  echo '未发现旧部署，直接全新安装'
fi

echo '== 3/7 停止旧服务并清除旧数据 =='
docker compose -p odk-erp down >/dev/null 2>&1 || true
[ -n "$OLD" ] && (cd "$OLD" && docker compose down >/dev/null 2>&1) || true
VOLS=$(docker volume ls -q --filter label=com.docker.compose.project=odk-erp 2>/dev/null)
[ -n "$VOLS" ] && docker volume rm -f $VOLS >/dev/null 2>&1 && echo "已清除旧数据卷" || echo '无旧数据卷'

echo '== 4/7 部署全新目录与配置 =='
echo '__B64__' | base64 -d > /tmp/odk_full_stack.tar.gz
rm -rf $DST
mkdir -p $DST
tar zxf /tmp/odk_full_stack.tar.gz -C $BASE
rm -f /tmp/odk_full_stack.tar.gz
cd $DST
[ -f .env ] || echo "POSTGRES_PASSWORD=odk_$(openssl rand -hex 8)" > .env
source .env
cat > odoo.conf <<EOF
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
echo "模块: $(ls addons | tr '\\n' ' ')"
echo "数据库密码: ${POSTGRES_PASSWORD}（已写入 .env，请妥善保存）"

echo '== 5/7 启动数据库 =='
docker compose up -d db
for i in $(seq 1 30); do
  docker compose exec -T db pg_isready -U odoo >/dev/null 2>&1 && break
  sleep 2
done
docker compose exec -T db pg_isready -U odoo

echo '== 6/7 全新初始化 Odoo（安装 11 个应用 + 简体中文，约 3-8 分钟） =='
docker compose run --rm odoo odoo -d odk_erp \\
  -i sale_management,purchase,mrp,odk_scan,odk_subcontract,odk_quality,odk_wms,odk_mrp_calc,odk_dispatch,odk_tech,odk_http_shim \\
  --without-demo=all --load-language=zh_CN --stop-after-init

echo '== 7/7 启动服务并验证 =='
docker compose up -d odoo
for i in $(seq 1 40); do
  curl -s -o /dev/null http://127.0.0.1:8069/web/login && break
  sleep 3
done
code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://127.0.0.1:8069/web/login || true)
code88=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://127.0.0.1:88/web/login || true)
echo "Odoo 8069: ${code:-无响应} | 88端口: ${code88:-无响应}"
if [ "$code" = "200" ] && [ "$code88" != "200" ]; then
  echo '>> 8069 就绪但 88 未通，尝试自动切换 nginx…'
  bash switch_nginx.sh || echo '>> nginx 未自动切换，可先用 http://IP:8069 访问'
  code88=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://127.0.0.1:88/web/login || true)
fi
if [ "$code" != "200" ]; then
  echo '!! Odoo 启动异常，最近日志：'
  docker compose logs --tail 50 odoo
  exit 1
fi
echo '============================================================'
echo ' 全新安装完成！'
echo ' 访问: http://220.162.99.166:88 （或 http://IP:8069）'
echo ' 账号: admin / admin   ←【登录后立即改密码】'
[ -n "$BK" ] && echo " 旧库备份: $BK"
[ -n "$OLD" ] && echo " 旧目录保留在: $OLD（确认无误后可删除）"
echo ' 请回到对话窗口告知技术，远程完成上线验收与配置指导。'
echo '============================================================'
""".replace("__B64__", b64)

with open(SH, 'w') as f:
    f.write(script)
os.chmod(SH, 0o755)
print('安装脚本: %s (%.1f KB)' % (SH, os.path.getsize(SH) / 1024))

# 自检：脚本内嵌包可还原且关键文件齐全
b64_in = open(SH).read().split("| base64 -d", 1)[0].rsplit("echo '", 1)[1]
tf2 = tarfile.open(fileobj=io.BytesIO(base64.b64decode(b64_in)), mode="r:gz")
n2 = tf2.getnames()
assert 'deploy_odoo/docker-compose.yml' in n2
assert 'deploy_odoo/addons/odk_dispatch/__manifest__.py' in n2
print('脚本自检 OK（含 compose/8 模块/switch_nginx）')

# ---------- 3) 上传附件 ----------
def call(service, method, *args):
    payload = {'jsonrpc': '2.0', 'method': 'call',
               'params': {'service': service, 'method': method, 'args': list(args)}}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL + '/jsonrpc', data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(str(out['error'])[:400])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


old = ex('ir.attachment', 'search',
         [('name', 'in', ('odk_reinstall.sh', 'odk_install_all.sh'))], limit=20)
if old:
    ex('ir.attachment', 'unlink', old)
    print('已清理旧附件 %d 个' % len(old))

raw_sh = open(SH, 'rb').read()
att = ex('ir.attachment', 'create', {
    'name': 'odk_install_all.sh',
    'db_datas': base64.b64encode(raw_sh).decode(),
    'mimetype': 'text/x-shellscript',
    'public': True, 'type': 'binary'})
print('附件已创建 id=%s' % att)
dl = URL + '/web/content/%s?download=true' % att
with urllib.request.urlopen(dl, timeout=60) as resp:
    body = resp.read()
assert body == raw_sh
print('下载验证: HTTP 200 | %.1f KB | 一致 ✓' % (len(body) / 1024))
print()
print("服务器执行命令：")
print("cd /www/wwwroot && wget -q '%s' -O install_all.sh && bash install_all.sh" % dl)
