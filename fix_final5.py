#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复5：首页$→¥ + shell翻译重载 + 重启Odoo"""
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=900):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError('%s/%s: %s' % (model, method, json.dumps(d['error'], ensure_ascii=False)[:400]))
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)

# 1. 首页 $ → ¥
view = rpc('ir.ui.view', 'read', [[3001]], {'fields': ['arch_db']})[0]
arch = view['arch_db']
n = arch.count('$ ')
arch = arch.replace('$ ', '¥ ')
rpc('ir.ui.view', 'write', [[3001], {'arch_db': arch}])
print('首页货币替换: %d 处 $ → ¥ ✓' % n)

# 2. 页脚结构（顺便看）
fc = rpc('ir.ui.view', 'read', [[2372]], {'fields': ['key', 'arch_db']})[0]
print('footer_custom arch 长度:', len(fc['arch_db']))
print(fc['arch_db'][:2500])
