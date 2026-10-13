#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修正：12 款奥登科户外鞋归类 + 补 BOM"""
import json

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=900):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

# 可售但无分类的产品
fgs = rpc('product.template', 'search_read', [[['sale_ok', '=', True], ['categ_id', '=', False]]],
          {'fields': ['name', 'default_code', 'categ_id']})
print('可售无分类产品 (%d):' % len(fgs))
for p in fgs:
    print('  - %s (%s)' % (p['name'], p.get('default_code')))

# 成品鞋分类
cats = rpc('product.category', 'search_read', [[['name', '=', '成品鞋']]], {'fields': ['id']})
cat_id = cats[0]['id']

# 归类
if fgs:
    rpc('product.template', 'write', [[p['id'] for p in fgs], {'categ_id': cat_id}])
    print('已归入成品鞋分类: %d 款' % len(fgs))

# 建 BOM（以男士休闲皮鞋 BOM 为模板）
src_bom = rpc('mrp.bom', 'search_read', [[['code', '=', 'BOM-SHO-042']]],
              {'fields': ['id', 'code']})
if src_bom:
    src_id = src_bom[0]['id']
    for p in fgs:
        ex = rpc('mrp.bom', 'search_count', [[['product_tmpl_id', '=', p['id']]]])
        if ex:
            print('  已有 BOM: %s' % p['name'][:16])
            continue
        new_id = rpc('mrp.bom', 'copy', [[src_id]], {'default_product_tmpl_id': p['id']})
        rpc('mrp.bom', 'write', [[new_id], {'code': 'BOM-%s' % (p.get('default_code') or p['id'])}])
        print('  ✓ BOM-%s → %s' % (p.get('default_code') or p['id'], p['name'][:20]))

nb = rpc('mrp.bom', 'search_count', [[]])
print('\nBOM 总数: %s' % nb)
