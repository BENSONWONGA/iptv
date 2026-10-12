#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复列表表头：替换 lists.scss → 重启 → 升级 → 验证"""
import base64
import json
import time

import requests
from bt_exec import BTExec

TARGET = '/opt/odoo20/addons/theme_liquid_glass/static/src/scss/lists.scss'
SRC = '/tmp/lists_fixed.scss'

ex = BTExec()
b64 = base64.b64encode(open(SRC, 'rb').read()).decode()
print('新 lists.scss base64 长度:', len(b64))

cmd = (
    "echo -n %s | base64 -d > /tmp/lists_new.scss && "
    "cp %s %s.bak && "
    "cp /tmp/lists_new.scss %s && "
    "chown odoo20:odoo20 %s %s.bak && "
    "grep -c 'ShoeFactory 修复' %s && echo PATCH_OK"
) % (b64, TARGET, TARGET, TARGET, TARGET, TARGET, TARGET)
out = ex.run(cmd, timeout=40)
print(out[out.find('XMK'):] if 'XMK' in out else out)
assert 'PATCH_OK' in out, '写入失败'
print('lists.scss 已替换 ✓（原文件备份 .bak）')

# 重启
ex.run('systemctl restart odoo20', timeout=30)
time.sleep(9)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=20)
assert 'ACTIVE_OK' in out, out
print('Odoo 重启 ✓')

# 升级模块重建资产
HOST = 'http://220.162.99.166:9000'
s = requests.Session()
r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
uid = r.json()['result']['uid']
print('RPC 登录 ✓ uid=%s' % uid)


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
print('theme_liquid_glass 升级 ✓')

# 验证编译产物包含新规则
import re
r = s.get(HOST + '/odoo/manufacturing', timeout=60)
css_urls = set(re.findall(r'(/web/assets/[^"\']+\.css)', r.text))
found = False
for u in css_urls:
    css = s.get(HOST + u, timeout=60).text
    if 'rgba(8, 16, 30, 0.55)' in css or 'rgba(8,16,30,.55)' in css:
        found = True
        print('编译产物含新表头底色 ✓ (%s)' % u.split('/')[-1])
        break
assert found, '新规则未进编译产物'
print('全部完成 ✓')
