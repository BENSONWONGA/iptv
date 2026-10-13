#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复2：菜单/电话/翻译/页脚诊断"""
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

# 1. 菜单现状
menus = rpc('website.menu', 'search_read', [[['website_id', '=', 1]]],
            {'fields': ['name', 'url', 'parent_id', 'sequence'], 'order': 'parent_id,sequence,id'})
print('=== 菜单 ===')
for m in menus:
    print(m['id'], '|', m['name'], '|', m['url'], '| parent:', m['parent_id'] and m['parent_id'][0], '| seq:', m['sequence'])

# 2. website 当前设置
w = rpc('website', 'read', [[1]], {'fields': ['name', 'phone', 'email', 'social_twitter', 'social_linkedin',
                                               'social_facebook', 'social_instagram', 'social_github', 'social_youtube']})[0]
print('\n=== website ===')
print(w)

# 3. 公司 partner
comp = rpc('res.company', 'read', [[1]], {'fields': ['partner_id']})[0]['partner_id']
p = rpc('res.partner', 'read', [[comp[0]]], {'fields': ['name', 'email', 'phone', 'street', 'city']})[0]
print('公司 partner:', p)

# 4. 尝试更新翻译（website_sale）
try:
    mods = rpc('ir.module.module', 'search', [[['name', 'in', ['website_sale', 'website', 'sale']]]])
    r = rpc('ir.module.module', 'button_update_translations', [mods], timeout=600)
    print('翻译更新 OK:', r)
except Exception as e:
    print('翻译更新失败:', str(e)[:200])

# 5. 安装语言检查
langs = rpc('res.lang', 'search_read', [[]], {'fields': ['code', 'name', 'active']})
print('语言:', langs)

# 6. footer 默认 view key 检查
for key in ['website.footer_custom', 'website.footer_default']:
    v = rpc('ir.ui.view', 'search_read', [[['key', '=', key]]], {'fields': ['id', 'key', 'website_id']})
    print(key, '=>', v)
