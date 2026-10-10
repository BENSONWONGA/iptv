#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包全套 11 模块 → 生成线上全新重装脚本 → 上传 Odoo 附件 → 验证下载"""
import base64
import io
import json
import os
import tarfile
import urllib.request

ADDONS = "/workspace/deploy_odoo/addons"
TGZ = "/workspace/odk_addons_latest.tar.gz"
SH = "/workspace/odk_reinstall.sh"
MODULES = 8

URL = 'http://220.162.99.166:88'
DB, USER, PWD = 'odk_erp', 'admin', 'admin'

# ---------- 1) 打包（排除 __pycache__/pyc） ----------
def skip(t):
    b = os.path.basename(t.name)
    if b == "__pycache__" or b.endswith(".pyc"):
        return None
    return t

with tarfile.open(TGZ, "w:gz") as tf:
    tf.add(ADDONS, arcname="addons", filter=skip)
names = [n for n in tarfile.open(TGZ).getnames()]
mods = sorted({n.split('/')[1] for n in names if n.count('/') >= 1 and n != 'addons'})
print("打包: %.1f KB | 模块 %d 个: %s" % (os.path.getsize(TGZ) / 1024, len(mods), mods))
assert len(mods) == MODULES, "模块数不符: %d" % len(mods)
assert 'odk_dispatch' in mods and 'odk_tech' in mods and 'odk_http_shim' in mods

# 校验 odk_dispatch 是修复版
with tarfile.open(TGZ) as tf:
    m = tf.extractfile("addons/odk_dispatch/__manifest__.py").read().decode()
    assert '"depends": ["odk_wms", "mrp", "web"]' in m and '"version": "20.0.2.0.2"' in m
    v = tf.extractfile("addons/odk_dispatch/views/barcode_views.xml").read().decode()
    assert 'report_file' not in v
print("校验 OK: odk_dispatch = v20.0.2.0.2（report 依赖+report_file 均已修复）")

# ---------- 2) 生成重装脚本 ----------
b64 = base64.b64encode(open(TGZ, "rb").read()).decode()
script = """#!/bin/bash
# ============================================================
# 奥登科 ERP · 线上全新重装脚本（Odoo 20 + 11 个自研模块 + 中文）
# 动作：备份旧库 → 换最新模块 → 清空数据卷 → 全新初始化 → 验证
# 全程约 5-10 分钟，失败会停在哪一步一目了然
# ============================================================
set -e
BASE=/www/wwwroot
[ -d $BASE/deploy_odoo ] || { echo "!! 未找到 $BASE/deploy_odoo"; exit 1; }
cd $BASE

echo '== 1/6 备份现有数据库（保底可回滚） =='
BK=$BASE/backup_odk_erp_$(date +%Y%m%d_%H%M%S).sql
cd deploy_odoo
docker compose exec -T db pg_dump -U odoo odk_erp > "$BK"
[ -s "$BK" ] && echo "备份完成: $BK ($(du -h "$BK" | cut -f1))"

echo '== 2/6 部署最新全套模块（11 个） =='
cd $BASE
echo '__B64__' | base64 -d > odk_addons_latest.tar.gz
tar zxf odk_addons_latest.tar.gz
rm -rf deploy_odoo/addons/odk_*
cp -a addons/odk_* deploy_odoo/addons/
rm -rf addons odk_addons_latest.tar.gz
ls deploy_odoo/addons/

echo '== 3/6 停止服务并清除旧数据（全新开始） =='
cd $BASE/deploy_odoo
docker compose down
VOLS=$(docker volume ls -q --filter label=com.docker.compose.project=odk-erp)
[ -n "$VOLS" ] && docker volume rm -f $VOLS && echo "已清除数据卷: $VOLS"

echo '== 4/6 启动数据库 =='
docker compose up -d db
for i in $(seq 1 30); do
  docker compose exec -T db pg_isready -U odoo >/dev/null 2>&1 && break
  sleep 2
done
docker compose exec -T db pg_isready -U odoo

echo '== 5/6 全新初始化（安装 11 模块 + 中文，约 3-8 分钟） =='
docker compose run --rm odoo odoo -d odk_erp \\
  -i sale_management,purchase,mrp,odk_scan,odk_subcontract,odk_quality,odk_wms,odk_mrp_calc,odk_dispatch,odk_tech,odk_http_shim \\
  --without-demo=all --load-language=zh_CN --stop-after-init

echo '== 6/6 启动并验证 =='
docker compose up -d odoo
for i in $(seq 1 40); do
  curl -s -o /dev/null http://127.0.0.1:8069/web/login && break
  sleep 3
done
code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://127.0.0.1:8069/web/login || true)
code88=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://127.0.0.1:88/web/login || true)
echo "Odoo 8069: ${code:-无响应} | 外部 88: ${code88:-无响应}"
if [ "$code88" != "200" ]; then
  echo '!! 启动异常，最后日志：'
  docker compose logs --tail 40 odoo
  exit 1
fi
echo '============================================================'
echo ' 全新安装完成！'
echo ' 访问: http://220.162.99.166:88   账号: admin / admin'
echo ' 旧库备份: '"$BK"
echo' 请回到对话窗口告知技术，远程完成上线验收与配置指导。'
echo '============================================================'
""".replace("__B64__", b64)

with open(SH, "w") as f:
    f.write(script)
os.chmod(SH, 0o755)
print("重装脚本: %s (%.1f KB)" % (SH, os.path.getsize(SH) / 1024))

# 自检：脚本内嵌包可还原
sh_txt = open(SH).read()
b64_in = sh_txt.split("| base64 -d", 1)[0].rsplit("echo '", 1)[1]
raw2 = base64.b64decode(b64_in)
tf2 = tarfile.open(fileobj=io.BytesIO(raw2), mode="r:gz")
m2 = tf2.extractfile("addons/odk_dispatch/__manifest__.py").read().decode()
assert "20.0.2.0.2" in m2
print("脚本自检 OK")

# ---------- 3) 上传附件（Odoo 20: db_datas 直写） ----------
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
         [('name', 'in', ('odk_reinstall.sh', 'odk_dispatch_fix.sh', 'odk_fix.sh'))],
         limit=20)
if old:
    ex('ir.attachment', 'unlink', old)
    print('已清理旧附件 %d 个' % len(old))

raw_sh = open(SH, 'rb').read()
att = ex('ir.attachment', 'create', {
    'name': 'odk_reinstall.sh',
    'db_datas': base64.b64encode(raw_sh).decode(),
    'mimetype': 'text/x-shellscript',
    'public': True, 'type': 'binary'})
print('附件已创建 id=%s' % att)

dl = URL + '/web/content/%s?download=true' % att
with urllib.request.urlopen(dl, timeout=60) as resp:
    body = resp.read()
assert body == raw_sh, '下载内容不一致!'
print('下载验证: HTTP 200 | %d 字节 | 一致 ✓' % len(body))
print()
print('下载地址: %s' % dl)
print()
print("服务器执行命令：")
print("cd /www/wwwroot && wget -q '%s' -O reinstall.sh && bash reinstall.sh" % dl)
