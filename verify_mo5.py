#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MO/00005 收尾验证：成品库存 + 工时总账 + 工单终态"""
import json

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=300):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'params': {'model': model, 'method': method,
                                     'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'])[:250])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

mo_id = rpc('mrp.production', 'search_read', [[['name', '=', 'WH/MO/00005']]],
            {'fields': ['id']})[0]['id']

# 成品库存（经模板找变体）
tmpl = rpc('product.template', 'search_read', [[['default_code', '=', 'ADK-T001']]],
           {'fields': ['name']})[0]
prod = rpc('product.product', 'search_read', [[['product_tmpl_id', '=', tmpl['id']]]],
           {'fields': ['qty_available']})[0]
print('猎鹰TX 成品库存: %s 双（此前 0，预期 +20）' % prod['qty_available'])

# 工时总账
prods = rpc('mrp.workcenter.productivity', 'search_read',
            [[['workorder_id.production_id', '=', mo_id]]],
            {'fields': ['workorder_id', 'employee_id', 'duration']})
by_emp = {}
for p in prods:
    emp = p['employee_id'][1] if p.get('employee_id') else '未标记'
    by_emp.setdefault(emp, 0.0)
    by_emp[emp] += p['duration'] or 0
print('\n===== MO/00005 工时总账 =====')
for emp, dur in by_emp.items():
    print('  %s: %.1f 分钟' % (emp, dur))

# 工单终态
wos = rpc('mrp.workorder', 'search_read', [[['production_id', '=', mo_id]]],
          {'fields': ['name', 'state', 'qty_produced', 'duration']})
print('\n===== 工单终态 =====')
for w in sorted(wos, key=lambda x: x['id']):
    print('  %-8s [%s] %s双 %s分钟' % (w['name'], w['state'], w['qty_produced'], round(w['duration'], 1)))

# 组件消耗验证（10 种材料应被消耗）
moves = rpc('stock.move', 'search_read', [[['raw_material_production_id', '=', mo_id]]],
            {'fields': ['product_id', 'quantity', 'picked']})
consumed = sum(1 for m in moves if m.get('picked'))
print('\n组件: %d/%d 已消耗' % (consumed, len(moves)))
