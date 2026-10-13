#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断+修复附件、货币、CSS"""
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
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)

# 1. 附件诊断
atts = rpc('ir.attachment', 'search_read', [[['name', 'in', ['adk_hero_mountain.jpg', 'adk_brand_story.jpg']]]],
           {'fields': ['name', 'public', 'mimetype', 'res_model', 'res_id', 'type', 'url', 'website_id']})
print('附件:', json.dumps(atts, ensure_ascii=False, default=str))
for a in atts:
    raw = rpc('ir.attachment', 'read', [[a['id']]], {'fields': ['datas']})[0]
    print(a['name'], 'datas长度:', len(raw.get('datas') or ''))

# 2. 业务数据量（决定货币改法）
so = rpc('sale.order', 'search_count', [[]])
am = rpc('account.move', 'search_count', [[]])
inv = rpc('account.move', 'search_count', [[['move_type', '=', 'out_invoice']]])
print('sale.order:', so, '| account.move:', am, '| 销售发票:', inv)

# 3. CNY 货币存在性
cny = rpc('res.currency', 'search_read', [[['name', 'in', ['CNY', 'RMB']]]], {'fields': ['name', 'symbol', 'active']})
print('CNY:', cny)

# 4. website pricelist
w = rpc('website', 'read', [[1]], {'fields': ['pricelist_id', 'pricelist_ids']})[0]
print('website pricelist:', w)
pl = rpc('product.pricelist', 'search_read', [[]], {'fields': ['name', 'currency_id', 'website_id']})
print('pricelists:', pl)
