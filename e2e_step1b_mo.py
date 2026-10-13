#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端 第1b步：重建 MO（带 BOM）→ 确认 → 组件分析"""
import json

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

state = json.load(open('/tmp/e2e_state.json'))
mo_id, prod_id = state['mo_id'], state['prod_id']

# 1. 取消空 MO
rpc('mrp.production', 'action_cancel', [[mo_id]])
print('旧 MO 已取消')

# 2. 找模板的 BOM
tmpl = rpc('product.product', 'read', [prod_id], {'fields': ['product_tmpl_id']})[0]['product_tmpl_id'][0]
bom = rpc('mrp.bom', 'search_read', [[['product_tmpl_id', '=', tmpl]]], {'fields': ['id', 'code']})[0]
print('BOM: %s (id=%s)' % (bom['code'], bom['id']))

# 3. 重建 MO
mo_id = rpc('mrp.production', 'create', [{
    'product_id': prod_id,
    'product_qty': 30,
    'bom_id': bom['id'],
    'origin': state['so_name'],
}])
rpc('mrp.production', 'action_confirm', [[mo_id]])
mo = rpc('mrp.production', 'read', [mo_id],
         {'fields': ['name', 'state', 'components_availability', 'workorder_ids']})[0]
print('MO: %s | %s | 组件可用性: %s | 工单: %s' % (mo['name'], mo['state'], mo.get('components_availability'), mo.get('workorder_ids')))

# 4. 组件分析
print('===== 组件清单 =====')
moves = rpc('stock.move', 'search_read', [[['raw_material_production_id', '=', mo_id]]],
            {'fields': ['product_id', 'product_uom_qty', 'forecast_availability']})
shortage = []
for mv in moves:
    av = mv.get('forecast_availability', 0) or 0
    need = mv['product_uom_qty']
    mark = 'OK' if av >= need else '缺料'
    print('  %-24s 需 %7.2f 可用 %7.2f  %s' % (mv['product_id'][1][:24], need, av, mark))
    if av < need:
        shortage.append((mv['product_id'][0], mv['product_id'][1], need, av))
print('缺料组件: %d 个' % len(shortage))

state['mo_id'] = mo_id
state['mo_name'] = mo['name']
state['shortage'] = shortage
json.dump(state, open('/tmp/e2e_state.json', 'w'))
print('MO=%s(id=%s) 已更新' % (mo['name'], mo_id))
