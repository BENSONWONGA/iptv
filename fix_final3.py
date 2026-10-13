#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复3：website字段探测 + 联系信息 + 翻译更新"""
import json

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
        raise RuntimeError('%s/%s: %s' % (model, method, json.dumps(d['error'], ensure_ascii=False)[:400]))
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)

# 1. website 字段
fields = rpc('website', 'fields_get', [], {'attributes': ['string', 'type']})
interesting = {k: v['string'] for k, v in fields.items()
               if any(x in k for x in ['phone', 'email', 'social', 'street', 'city'])}
print('website 相关字段:', json.dumps(interesting, ensure_ascii=False, indent=1))

# 2. 公司联系信息 → 奥登科
comp = rpc('res.company', 'read', [[1]], {'fields': ['partner_id']})[0]['partner_id']
rpc('res.partner', 'write', [[comp[0]], {
    'email': 'service@audenko-outdoor.com',
    'phone': '+86 595-8888 6666',
    'street': '陈埭镇鞋都路 188 号',
    'city': '晋江市',
    'zip': '362211',
}])
print('公司联系信息已更新 ✓')

# 3. 翻译更新（website_sale / website）
try:
    mods = rpc('ir.module.module', 'search', [[['name', 'in', ['website_sale', 'website', 'sale', 'theme_default']]]])
    print('模块 ids:', mods)
    r = rpc('ir.module.module', 'button_update_translations', [mods], timeout=900)
    print('翻译更新 OK')
except Exception as e:
    print('button_update_translations 失败:', str(e)[:300])
    # 备选：base.language.install wizard
    try:
        wiz = rpc('base.language.install', 'create', [{'lang_ids': [[6, 0, [1]]], 'overwrite': True}])
        rpc('base.language.install', 'button_install", [[wiz]]'.replace('"', ''), timeout=900)
        print('wizard 翻译安装 OK')
    except Exception as e2:
        print('wizard 也失败:', str(e2)[:300])

# 4. 语言
langs = rpc('res.lang', 'search_read', [[]], {'fields': ['code', 'name', 'active']})
print('语言:', langs)

# 5. footer views
for key in ['website.footer_custom', 'website.footer_default']:
    v = rpc('ir.ui.view', 'search_read', [[['key', '=', key]]], {'fields': ['id', 'key', 'website_id']})
    print(key, '=>', v)
