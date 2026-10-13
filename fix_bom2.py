#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给成品鞋分类下无 BOM 的产品补 BOM"""
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

cats = rpc('product.category', 'search_read', [[['name', '=', '成品鞋']]], {'fields': ['id']})
cat_id = cats[0]['id']
fgs = rpc('product.template', 'search_read', [[['categ_id', '=', cat_id]]],
          {'fields': ['name', 'default_code']})
print('成品鞋 (%d 款):' % len(fgs))

src_bom = rpc('mrp.bom', 'search_read', [[['code', '=', 'BOM-SHO-042']]], {'fields': ['id']})
src_id = src_bom[0]['id']

created = 0
for p in fgs:
    ex = rpc('mrp.bom', 'search_count', [[['product_tmpl_id', '=', p['id']]]])
    if ex:
        continue
    new_id = rpc('mrp.bom', 'copy', [[src_id]])
    rpc('mrp.bom', 'write', [[new_id], {'product_tmpl_id': p['id'],
                                       'code': 'BOM-%s' % (p.get('default_code') or p['id'])}])
    print('  ✓ BOM-%s → %s' % (p.get('default_code'), p['name'][:20]))
    created += 1

nb = rpc('mrp.bom', 'search_count', [[]])
print('新建 %d, BOM 总数: %s' % (created, nb))
