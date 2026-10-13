#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 adk_outdoor.css 引用：找出所有引用 theme_liquid_glass 路径的 asset/view 记录"""
import json

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
ex = BTExec()
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=300):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

# 1. ir_asset 引用
assets = rpc('ir.asset', 'search_read', [[]], {'fields': ['name', 'bundle', 'directive', 'path', 'active']})
print('=== ir.asset 全部记录 (%d) ===' % len(assets))
for a in assets:
    print('  id=%s %s | bundle=%s | %s | path=%s | active=%s' % (
        a['id'], a['name'], a['bundle'], a['directive'], a['path'], a['active']))

# 2. 视图里引用 adk_outdoor / theme_liquid_glass 的
views = rpc('ir.ui.view', 'search_read', [[['arch_db', 'ilike', 'adk_outdoor']]],
            {'fields': ['name', 'key', 'model', 'website_id'], 'limit': 20})
print('=== arch 引用 adk_outdoor 的视图 (%d) ===' % len(views))
for v in views:
    print('  id=%s key=%s model=%s ws=%s' % (v['id'], v.get('key'), v.get('model'), v.get('website_id')))

# 3. 服务器上 adk_outdoor.css 的实际位置
out = ex.run('find /opt/odoo20/addons -name "adk_outdoor.css" 2>/dev/null; ls /opt/odoo20/addons/theme_liquid_glass/static/src/scss/ 2>/dev/null | head; echo ---; ls /opt/odoo20/addons/ | grep -iE "adk|shoe|custom"',
             timeout=40, name='adk-diag')
print('=== 服务器文件 ===')
print(out)
