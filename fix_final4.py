#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复4：翻译重载(wizard) + 页脚结构检查"""
import json

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

# 1. 翻译重载 wizard（zh_CN id=12, overwrite=True）
wiz_id = rpc('base.language.install', 'create', [{'lang_ids': [(6, 0, [12])], 'overwrite': True}])
print('wizard:', wiz_id)
res = rpc('base.language.install', 'button_install', [[wiz_id]])
print('翻译重载结果:', res)

# 2. 页脚结构
fc = rpc('ir.ui.view', 'read', [[2372]], {'fields': ['key', 'arch_db']})[0]
print('\n=== footer_custom arch ===')
print(fc['arch_db'][:3000])
