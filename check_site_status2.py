#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查2：可用网站主题、当前网站、页面"""
import json
import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'

s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}},
    }, timeout=900)
    d = r.json()
    if 'error' in d:
        return {'__error__': json.dumps(d['error'], ensure_ascii=False)[:300]}
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
print('RPC 登录 ✓')

# 1. 所有可用的网站主题（theme_* 模块，依赖 website 的）
themes = rpc('ir.module.module', 'search_read', [[['name', 'like', 'theme_']]],
             {'fields': ['name', 'state', 'shortdesc']})
print('\n=== 主题模块 (%d) ===' % len(themes))
for m in sorted(themes, key=lambda x: x['name']):
    print('%-30s %-12s %s' % (m['name'], m['state'], (m.get('shortdesc') or '')[:40]))

# 2. 当前网站
websites = rpc('website', 'search_read', [[]], {'fields': ['name', 'domain']})
print('\n=== 网站 ===')
for w in websites:
    print(w['name'], '|', w.get('domain'))

# 3. 网站页面
pages = rpc('website.page', 'search_read', [[]], {'fields': ['name', 'url', 'website_published'], 'limit': 40})
print('\n=== 网站页面 ===')
if isinstance(pages, list):
    for p in pages:
        print('%-30s %-25s 发布:%s' % (p['name'], p['url'], p.get('website_published')))
else:
    print(pages)

# 4. 菜单
menus = rpc('website.menu', 'search_read', [[]], {'fields': ['name'], 'limit': 40})
print('\n=== 网站菜单 ===')
if isinstance(menus, list):
    print(', '.join(m['name'] for m in menus))
else:
    print(menus)

# 5. 已安装的所有模块（看网站相关能力）
installed = rpc('ir.module.module', 'search_read', [[['state', '=', 'installed'],
                                                      ['name', 'like', 'website']]],
                {'fields': ['name']})
print('\n=== 已安装的 website_* 模块 ===')
print(', '.join(m['name'] for m in installed))
