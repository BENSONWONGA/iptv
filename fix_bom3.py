#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给成品鞋补 BOM（读源结构 → 手动 create）"""
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
          {'fields': ['name', 'default_code', 'uom_id']})
print('成品鞋 (%d 款):' % len(fgs))

# 源 BOM 结构
src = rpc('mrp.bom', 'search_read', [[['code', '=', 'BOM-SHO-042']]],
          {'fields': ['id', 'product_qty', 'type', 'bom_line_ids', 'operation_ids']})[0]
lines = rpc('mrp.bom.line', 'search_read', [[['bom_id', '=', src['id']]]],
            {'fields': ['product_id', 'product_qty']})
ops = rpc('mrp.routing.workcenter', 'search_read', [[['bom_id', '=', src['id']]]],
          {'fields': ['name', 'workcenter_id', 'time_cycle_manual', 'sequence']})
print('源 BOM: %d 材料行, %d 工序' % (len(lines), len(ops)))

created = 0
for p in fgs:
    ex = rpc('mrp.bom', 'search_count', [[['product_tmpl_id', '=', p['id']]]])
    if ex:
        continue
    # create BOM
    bom_id = rpc('mrp.bom', 'create', [{
        'product_tmpl_id': p['id'],
        'code': 'BOM-%s' % (p.get('default_code') or p['id']),
        'product_qty': src['product_qty'],
        'type': src['type'],
    }])
    # create 材料行
    for ln in lines:
        rpc('mrp.bom.line', 'create', [{
            'bom_id': bom_id,
            'product_id': ln['product_id'][0],
            'product_qty': ln['product_qty'],
        }])
    # create 工序
    for op in ops:
        rpc('mrp.routing.workcenter', 'create', [{
            'bom_id': bom_id,
            'name': op['name'],
            'workcenter_id': op['workcenter_id'][0],
            'time_cycle_manual': op['time_cycle_manual'],
            'sequence': op['sequence'],
        }])
    print('  ✓ BOM-%s → %s (10行+5工序)' % (p.get('default_code'), p['name'][:20]))
    created += 1

nb = rpc('mrp.bom', 'search_count', [[]])
nl = rpc('mrp.bom.line', 'search_count', [[]])
no = rpc('mrp.routing.workcenter', 'search_count', [[]])
print('新建 %d | BOM 总数: %s | 材料行: %s | 工序: %s' % (created, nb, nl, no))
