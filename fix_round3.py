#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第三轮修复：上传新CSS + 菜单深查 + 页头电话来源"""
import base64
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)

# 1. 上传新 CSS
from bt_exec import BTExec
ex = BTExec()
b64 = base64.b64encode(open('/workspace/adk_outdoor.css', 'rb').read()).decode()
chunks = [b64[i:i + 60000] for i in range(0, len(b64), 60000)]
ex.run('rm -f /tmp/adk.b64', timeout=15, name='adk-css2')
for c in chunks:
    ex.run("echo -n %s >> /tmp/adk.b64" % c, timeout=15, name='adk-css2')
out = ex.run('base64 -d /tmp/adk.b64 > /opt/odoo20/addons/theme_liquid_glass/static/src/css/adk_outdoor.css && '
             'chown odoo20:odoo20 /opt/odoo20/addons/theme_liquid_glass/static/src/css/adk_outdoor.css && '
             'rm -f /tmp/adk.b64 && echo CSS_OK', timeout=30, name='adk-css2')
print('CSS 上传:', 'OK' if 'CSS_OK' in out else out[-200:])

# 2. 菜单深查（含所有 website）
menus = rpc('website.menu', 'search_read', [[]],
            {'fields': ['name', 'url', 'parent_id', 'sequence', 'website_id', 'is_visible'],
             'order': 'id'})
print('=== 全部菜单 ===')
for m in menus:
    print(m['id'], '|', m['name'], '|', m['url'], '| parent:', m['parent_id'] and m['parent_id'][0],
          '| ws:', m['website_id'], '| seq:', m['sequence'], '| vis:', m['is_visible'])

# 3. 页头电话来源：查 header 里的电话
out2 = ex.run("grep -rn '555-555' /opt/odoo20/addons/website/views/*.xml /opt/odoo20/addons/website/templates/*.xml 2>/dev/null | head -5",
              timeout=30, name='peek19')
print('=== 电话来源 ===')
print(out2[:1500])
