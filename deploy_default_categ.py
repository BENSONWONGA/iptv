#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署 product_list_default_categ.js 到 theme_liquid_glass → 注册资产 → 升级重建"""
import base64
import json
import time

import requests
from bt_exec import BTExec

MOD = '/opt/odoo20/addons/theme_liquid_glass'
JS = MOD + '/static/src/js/product_default_categ.js'
MANIFEST = MOD + '/__manifest__.py'

ex = BTExec()
b64 = base64.b64encode(open('/tmp/product_default_categ.js', 'rb').read()).decode()

cmd = (
    "echo -n %s | base64 -d > %s && chown odoo20:odoo20 %s && "
    # 幂等注册到 manifest 的 assets_backend
    "grep -q product_default_categ.js %s || "
    "sed -i \"s#'theme_liquid_glass/static/src/js/navbar_sidebar.js',#'theme_liquid_glass/static/src/js/navbar_sidebar.js',\\n            'theme_liquid_glass/static/src/js/product_default_categ.js',#\" %s && "
    "grep -n product_default_categ %s && echo PATCH_OK"
) % (b64, JS, JS, MANIFEST, MANIFEST, MANIFEST)
out = ex.run(cmd, timeout=40)
print(out[out.find('XMK'):] if 'XMK' in out else out)
assert 'PATCH_OK' in out, '写入失败'
print('JS + manifest 注册 ✓')

# 重启 + 升级
ex.run('systemctl restart odoo20', timeout=30)
time.sleep(9)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=20)
assert 'ACTIVE_OK' in out, out
print('Odoo 重启 ✓')

HOST = 'http://220.162.99.166:9000'
s = requests.Session()
r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=600)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


ids = rpc('ir.module.module', 'search', [[['name', '=', 'theme_liquid_glass']]])
rpc('ir.module.module', 'button_immediate_upgrade', [ids])
print('模块升级（资产重建）✓')

# 验证 bundle 包含补丁
import re
r = s.get(HOST + '/odoo/manufacturing', timeout=120)
js_urls = set(re.findall(r'(/web/assets/[^"\']+\.js)', r.text))
found = False
for u in js_urls:
    js = s.get(HOST + u, timeout=120).text
    if 'product_default_categ' in js or 'default_categ_id' in js:
        found = True
        print('bundle 含补丁代码 ✓ (%s)' % u.split('/')[-1])
        break
assert found, '补丁未进 bundle'
print('部署完成 ✓')
