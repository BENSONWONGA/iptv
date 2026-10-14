#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断：为什么通讯录个人出现在供应商列表"""
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
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

print('===== 供应商标记者（supplier_rank>0）=====')
sups = rpc('res.partner', 'search_read', [[['supplier_rank', '>', 0]]],
           {'fields': ['name', 'supplier_rank', 'customer_rank']})
for p in sups:
    print('  %s (供应商分:%s 客户分:%s)' % (p['name'], p['supplier_rank'], p.get('customer_rank', 0)))

print('\n===== 客户标记者（customer_rank>0）=====')
custs = rpc('res.partner', 'search_read', [[['customer_rank', '>', 0]]],
            {'fields': ['name', 'supplier_rank', 'customer_rank']})
for p in custs:
    print('  %s (客户分:%s 供应商分:%s)' % (p['name'], p['customer_rank'], p.get('supplier_rank', 0)))

# 来源分析：这些个人名是否来自员工通讯录
print('\n===== 交叉核对：这些名字是否是员工/员工联系人 =====')
emp_names = set()
emps = rpc('hr.employee', 'search_read', [[]], {'fields': ['name', 'work_contact_id']})
for e in emps:
    emp_names.add(e['name'])
sup_names = [p['name'] for p in sups]
in_emp = [n for n in sup_names if n in emp_names]
print('供应商中与员工同名: %d 人: %s' % (len(in_emp), in_emp[:10]))

# 相关联系人（hr.employee 的 work_contact 会自动建 res.partner）
print('\n员工总数: %d, 员工关联联系人: %d 个' % (
    len(emps), sum(1 for e in emps if e.get('work_contact_id'))))
