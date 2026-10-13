#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 Odoo 网站/主题/产品 当前状态"""
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
if 'error' in r.json():
    print('登录失败:', r.json()['error'])
    raise SystemExit(1)
print('RPC 登录 ✓')

# 1. 网站相关模块状态
rpc('ir.module.module', 'update_list')
mods = rpc('ir.module.module', 'search_read', [[['name', 'in', [
    'website', 'website_sale', 'website_sale_wishlist', 'website_sale_comparison',
    'theme_liquid_glass', 'shoe_theme', 'sale_management', 'website_blog']]]],
    {'fields': ['name', 'state', 'shortdesc']})
print('\n=== 模块状态 ===')
for m in mods:
    print('%-28s %-12s %s' % (m['name'], m['state'], m.get('shortdesc') or ''))

# 2. 网站列表
websites = rpc('website', 'search_read', [[]], {'fields': ['name', 'domain', 'is_published']})
print('\n=== 网站 ===')
print(json.dumps(websites, ensure_ascii=False, default=str))

# 3. 产品
prods = rpc('product.template', 'search_read', [[['sale_ok', '=', True]]],
            {'fields': ['name', 'list_price', 'website_published', 'website_id', 'categ_id'], 'limit': 50})
print('\n=== 可销售产品 (%d) ===' % len(prods))
for p in prods:
    print('%-30s ¥%-8s 发布:%s' % (p['name'], p['list_price'], p.get('website_published')))

# 4. 产品分类（公开）
categs = rpc('product.public.category', 'search_read', [[]], {'fields': ['name']})
print('\n=== 网站商品分类 ===')
print(json.dumps(categs, ensure_ascii=False))

# 5. 网站页面
pages = rpc('website.page', 'search_read', [[]], {'fields': ['name', 'url', 'website_published'], 'limit': 30})
print('\n=== 网站页面 ===')
for p in pages:
    print('%-30s %-25s 发布:%s' % (p['name'], p['url'], p.get('website_published')))

# 6. 主题当前绑定的 website.theme 模块（检查 website_menu）
menus = rpc('website.menu', 'search_read', [[]], {'fields': ['name', 'website_id'], 'limit': 30})
print('\n=== 网站菜单 ===')
for m in menus:
    print(m['name'])

print('\n=== 检查完成 ===')
