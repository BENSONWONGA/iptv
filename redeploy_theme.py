#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量重部署 shoe_theme（含资产）→ 重启 → upgrade → 验证"""
import base64
import os
import time
import zipfile

THEME_DIR = '/workspace/shoe_theme'
ZIP_PATH = '/workspace/shoe_theme.zip'

if os.path.exists(ZIP_PATH):
    os.remove(ZIP_PATH)
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(THEME_DIR):
        for f in files:
            full = os.path.join(root, f)
            arc = os.path.join('shoe_theme', os.path.relpath(full, THEME_DIR))
            zf.write(full, arc)

from bt_exec import BTExec

ex = BTExec()
b64 = base64.b64encode(open(ZIP_PATH, 'rb').read()).decode()
chunks = [b64[i:i + 30000] for i in range(0, len(b64), 30000)]
print('分 %d 块上传' % len(chunks))
ex.run('rm -f /tmp/st.b64', timeout=15, name='theme-deploy')
for c in chunks:
    ex.run("echo -n %s >> /tmp/st.b64" % c, timeout=15, name='theme-deploy')
out = ex.run('base64 -d /tmp/st.b64 > /tmp/shoe_theme.zip && cd /opt/odoo20/addons && unzip -oq /tmp/shoe_theme.zip && '
             'chown -R odoo20:odoo20 /opt/odoo20/addons/shoe_theme && rm -f /tmp/st.b64 /tmp/shoe_theme.zip && echo UPLOAD_OK',
             timeout=30, name='theme-deploy')
assert 'UPLOAD_OK' in out, out
print('上传 ✓')

ex.run('systemctl restart odoo20', timeout=30, name='theme-deploy')
time.sleep(9)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=20, name='theme-deploy')
print('重启 ✓' if 'ACTIVE_OK' in out else out)

# upgrade 模块（重建资产 bundle）
import json
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()
r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
uid = r.json()['result']['uid']


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=600)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


ids = rpc('ir.module.module', 'search', [[['name', '=', 'shoe_theme']]])
rpc('ir.module.module', 'button_immediate_upgrade', [ids])
print('模块升级（资产重建）✓')

data = rpc('shoe.dashboard', 'get_dashboard_data', [])
print('KPI 数:', len(data['kpis']), '| 快捷入口:', len(data['shortcuts']))

# 验证新 JS 已进 bundle
r = s.get(HOST + '/shoe_theme/static/src/js/dashboard.js', timeout=30)
new_js = b'useState' not in r.content and b'this.render()' in r.content
print('新 JS 生效 ✓' if new_js else 'JS 内容异常!', '(%d 字节)' % len(r.content))
print('=== 部署完成 ===')
