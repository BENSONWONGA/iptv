#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仅更新 dashboard.py（Python 代码改动静重启即可）→ 重启 → 验证"""
import base64
import time

from bt_exec import BTExec

ex = BTExec()

src = open('/workspace/shoe_theme/models/dashboard.py', 'rb').read()
b64 = base64.b64encode(src).decode()
chunks = [b64[i:i + 30000] for i in range(0, len(b64), 30000)]
ex.run('rm -f /tmp/dp.b64', timeout=15, name='theme-deploy')
for c in chunks:
    ex.run("echo -n %s >> /tmp/dp.b64" % c, timeout=15, name='theme-deploy')
out = ex.run('base64 -d /tmp/dp.b64 > /opt/odoo20/addons/shoe_theme/models/dashboard.py && '
             'chown odoo20:odoo20 /opt/odoo20/addons/shoe_theme/models/dashboard.py && '
             'rm -f /tmp/dp.b64 && echo PY_OK', timeout=20, name='theme-deploy')
print('PY_OK' if 'PY_OK' in out else out)
assert 'PY_OK' in out

ex.run('systemctl restart odoo20', timeout=30, name='theme-deploy')
time.sleep(9)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=20, name='theme-deploy')
print('重启 ✓' if 'ACTIVE_OK' in out else out)

# 验证
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


data = rpc('shoe.dashboard', 'get_dashboard_data', [])
print('公司:', data['company'], '| 用户:', data['user'])
for k in data['kpis']:
    print('  %s: %s %s' % (k['label'], k['value'], k.get('badge', '')))
print('快捷入口:', [sc['label'] for sc in data['shortcuts']])
print('月度销售:', [(m['label'], m['short']) for m in data['months']])
print('最新订单数:', len(data['orders']))
print('=== 数据源验证通过 ===')
