#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复附件关联 + 检查货币/业务数据"""
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

# 1. 把 hero/brand 附件挂到首页 view 上（模拟网站编辑器媒体附件的标准存储方式）
rpc('ir.attachment', 'write', [[1618, 1619], {'res_model': 'ir.ui.view', 'res_id': 3001}])
print('附件已关联首页 view')

# 2. 业务数据量
so = rpc('sale.order', 'search_count', [[]])
am = rpc('account.move', 'search_count', [[]])
print('sale.order:', so, '| account.move:', am)

# 3. CNY
cny = rpc('res.currency', 'search_read', [[['name', 'in', ['CNY', 'RMB']]]],
          {'fields': ['name', 'symbol', 'active']})
print('CNY:', cny)

# 4. pricelist
pl = rpc('product.pricelist', 'search_read', [[]], {'fields': ['name', 'currency_id', 'website_id']})
print('pricelists:', pl)
