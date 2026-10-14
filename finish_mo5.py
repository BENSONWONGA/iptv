#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""续跑 MO/00005：绷帮成型→底部加工→包装 全部完工 → MO 收尾 → 成品入库验证"""
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
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

# 模拟不同工人选岗
emps = rpc('hr.employee', 'search_read', [[]], {'fields': ['name'], 'limit': 5})
FLOW = [('绷帮成型', emps[1]['id'], emps[1]['name']),
        ('底部加工', emps[2]['id'], emps[2]['name']),
        ('包装', emps[3]['id'], emps[3]['name'])]

print('===== 车间终端续跑 MO/00005 =====')
for op_name, emp_id, emp_name in FLOW:
    wo = rpc('mrp.workorder', 'search_read',
             [[['production_id', '=', mo_id], ['name', '=', op_name]]],
             {'fields': ['id', 'state']})[0]
    if wo['state'] == 'done':
        print('%s: 已完成，跳过' % op_name)
        continue
    print('%s [%s] ← 工人 %s' % (op_name, wo['state'], emp_name))
    # start
    rpc('mrp.workorder', 'button_start', [[wo['id']]])
    # 标记工人
    pids = [t['id'] for t in rpc('mrp.workcenter.productivity', 'search_read',
                                 [[['workorder_id', '=', wo['id']], ['employee_id', '=', False]]],
                                 {'fields': ['id']})]
    if pids:
        rpc('mrp.workcenter.productivity', 'write', [pids, {'employee_id': emp_id}])
    # 报工 20 + 完成
    rpc('mrp.workorder', 'write', [[wo['id']], {'qty_producing': 20}])
    rpc('mrp.workorder', 'button_finish', [[wo['id']]])
    w = rpc('mrp.workorder', 'read', [wo['id']],
            {'fields': ['state', 'qty_produced', 'duration']})[0]
    print('  → %s 产量 %s 用时 %.1f 分钟' % (w['state'], w['qty_produced'], w['duration']))
    time.sleep(1)

# MO 状态
mo = rpc('mrp.production', 'read', [mo_id],
         {'fields': ['name', 'state', 'product_qty', 'qty_producing']})[0]
print('\nMO 状态: %s（计划 %s）' % (mo['state'], mo['product_qty']))
if mo['state'] != 'done':
    print('收尾 MO ...')
    rpc('mrp.production', 'write', [[mo_id], {'qty_producing': 20}])
    rpc('mrp.production', 'button_mark_done', [[mo_id]])
    mo = rpc('mrp.production', 'read', [mo_id], {'fields': ['state']})[0]
    print('MO → %s' % mo['state'])

# 成品库存验证
time.sleep(2)
prod = rpc('product.product', 'search_read', [[['default_code', '=', 'ADK-T001']]],
           {'fields': ['qty_available']})[0]
print('\n猎鹰TX 成品库存: %s 双（此前 0，预期 +20）' % prod['qty_available'])

# 工时总账
prods = rpc('mrp.workcenter.productivity', 'search_read', [[['workorder_id.production_id', '=', mo_id]]],
            {'fields': ['workorder_id', 'employee_id', 'duration']})
print('\n===== MO/00005 工时总账 =====')
by_emp = {}
for p in prods:
    emp = p['employee_id'][1] if p.get('employee_id') else '未标记'
    by_emp.setdefault(emp, 0)
    by_emp[emp] += p['duration']
for emp, dur in by_emp.items():
    print('  %s: %.1f 分钟' % (emp, dur))

# 全部工单最终状态
wos = rpc('mrp.workorder', 'search_read', [[['production_id', '=', mo_id]]],
          {'fields': ['name', 'state', 'qty_produced']})
print('\n===== 工单终态 =====')
for w in wos:
    print('  %s [%s] %s双' % (w['name'], w['state'], w['qty_produced']))
print('\n=== MO/00005 全流程完成 ===')
