#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端 第1步：SO → MO → 组件缺料分析"""
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
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
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

# ===== 1. 创建并确认销售订单 =====
print('===== 1. 销售订单 =====')
custs = rpc('res.partner', 'search_read', [[['customer_rank', '>', 0], ['name', 'not ilike', '奥登科鞋业']]],
            {'fields': ['name'], 'limit': 3})
cust = custs[0]
print('客户: %s' % cust['name'])
tmpl = rpc('product.template', 'search_read', [[['default_code', '=', 'ADK-H001']]],
           {'fields': ['id', 'name', 'list_price']})[0]
prod = rpc('product.product', 'search_read', [[['product_tmpl_id', '=', tmpl['id']]]],
           {'fields': ['id', 'name', 'list_price', 'qty_available']})[0]
print('产品: %s 现有库存: %s' % (prod['name'], prod['qty_available']))

so_id = rpc('sale.order', 'create', [{
    'partner_id': cust['id'],
    'order_line': [(0, 0, {'product_id': prod['id'], 'product_uom_qty': 30,
                           'price_unit': prod['list_price']})],
}])
rpc('sale.order', 'action_confirm', [[so_id]])
so = rpc('sale.order', 'read', [so_id], {'fields': ['name', 'state', 'amount_total', 'picking_ids']})[0]
print('SO: %s | %s | ¥%s | 出库单: %s' % (so['name'], so['state'], so['amount_total'], so['picking_ids']))

# ===== 2. 创建制造订单 =====
print('===== 2. 制造订单 =====')
mo_id = rpc('mrp.production', 'create', [{
    'product_id': prod['id'],
    'product_qty': 30,
    'origin': so['name'],
}])
mo = rpc('mrp.production', 'read', [mo_id],
         {'fields': ['name', 'state', 'bom_id', 'product_qty', 'workorder_ids']})[0]
print('MO: %s | %s | BOM:%s | 数量:%s' % (mo['name'], mo['state'], mo['bom_id'], mo['product_qty']))

# 确认 MO
rpc('mrp.production', 'action_confirm', [[mo_id]])
mo = rpc('mrp.production', 'read', [mo_id],
         {'fields': ['name', 'state', 'components_availability']})[0]
print('确认后: %s | 组件可用性: %s' % (mo['state'], mo.get('components_availability')))

# ===== 3. 组件缺料分析 =====
print('===== 3. 组件缺料分析 =====')
moves = rpc('stock.move', 'search_read', [[['raw_material_production_id', '=', mo_id]]],
            {'fields': ['product_id', 'product_uom_qty', 'forecast_availability', 'state']})
shortage = []
for mv in moves:
    av = mv.get('forecast_availability', 0) or 0
    need = mv['product_uom_qty']
    mark = 'OK' if av >= need else '缺料'
    print('  %-22s 需 %6.2f 可用 %6.2f  %s' % (mv['product_id'][1][:22], need, av, mark))
    if av < need:
        shortage.append((mv['product_id'][0], mv['product_id'][1], need, av))

print('\n缺料组件: %d 个' % len(shortage))
print('SO=%s' % so['name'])
print('MO=%s(id=%s)' % (mo['name'], mo_id))
with open('/tmp/e2e_state.json', 'w') as f:
    json.dump({'so_id': so_id, 'so_name': so['name'], 'mo_id': mo_id, 'mo_name': mo['name'],
               'cust_id': cust['id'], 'prod_id': prod['id'], 'shortage': shortage}, f)
print('状态已存 /tmp/e2e_state.json')
