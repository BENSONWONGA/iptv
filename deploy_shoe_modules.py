#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署 shoe_plm + shoe_qms 到服务器并安装"""
import base64
import json
import time
import zipfile

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
ex = BTExec()

# ===== 1. 打包两个模块 =====
print('===== 1. 打包模块 =====')
zf = zipfile.ZipFile('/tmp/shoe_modules.zip', 'w', zipfile.ZIP_DEFLATED)
for mod in ['shoe_plm', 'shoe_qms']:
    base = '/workspace/custom_addons/%s' % mod
    import os
    for root, dirs, files in os.walk(base):
        for f in files:
            fp = os.path.join(root, f)
            zf.write(fp, '%s/%s' % (mod, os.path.relpath(fp, base)))
zf.close()
import os
print('打包: %.1f KB' % (os.path.getsize('/tmp/shoe_modules.zip') / 1024))

# ===== 2. 上传 =====
print('===== 2. 上传 =====')
raw = open('/tmp/shoe_modules.zip', 'rb').read()
b64 = base64.b64encode(raw).decode()
chunks = [b64[i:i + 60000] for i in range(0, len(b64), 60000)]
print('分 %d 块上传...' % len(chunks))
ex.run('rm -f /tmp/sm.b64', timeout=15, name='sm-deploy')
for c in chunks:
    ex.run("echo -n %s >> /tmp/sm.b64" % c, timeout=20, name='sm-deploy')
out = ex.run(
    'base64 -d /tmp/sm.b64 > /tmp/shoe_modules.zip && cd /tmp && rm -rf shoe_plm shoe_qms && '
    'unzip -q shoe_modules.zip && '
    'rm -rf /opt/odoo20/addons/shoe_plm /opt/odoo20/addons/shoe_qms && '
    'mv shoe_plm shoe_qms /opt/odoo20/addons/ && '
    'chown -R odoo20:odoo20 /opt/odoo20/addons/shoe_plm /opt/odoo20/addons/shoe_qms && '
    'rm -f /tmp/sm.b64 /tmp/shoe_modules.zip && '
    'ls /opt/odoo20/addons/shoe_plm/ /opt/odoo20/addons/shoe_qms/ && echo UP_OK',
    timeout=60, name='sm-deploy')
print('上传:', 'OK' if 'UP_OK' in out else out[-400:])
if 'UP_OK' not in out:
    raise SystemExit(1)

# ===== 3. 重启 + 安装 =====
print('===== 3. 重启并安装 =====')
ex.run('systemctl restart odoo20', timeout=90, name='sm-deploy')
time.sleep(12)

s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=900):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
rpc('ir.module.module', 'update_list')
for mod in ['shoe_plm', 'shoe_qms']:
    m = rpc('ir.module.module', 'search_read', [[['name', '=', mod]]], {'fields': ['name', 'state']})
    if not m:
        print('%s: 未识别!' % mod)
        continue
    if m[0]['state'] != 'installed':
        rpc('ir.module.module', 'button_immediate_install', [[m[0]['id']]])
        m2 = rpc('ir.module.module', 'search_read', [[['name', '=', mod]]], {'fields': ['state', 'latest_version']})
        print('%s: installed %s' % (mod, m2[0]['latest_version']))
    else:
        print('%s: 已是 installed' % mod)

print('=== 模块部署完成 ===')
