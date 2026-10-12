#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证组织架构录入结果"""
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=120)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

ORG = [
    ('业务部', None, 2), ('大货业务', '业务部', 3), ('样品开发', '业务部', 9),
    ('开发部', None, 1), ('开发室01', '开发部', 0), ('技转课', '开发室01', 5),
    ('开发设计课', '开发部', 9), ('制作课', '开发部', 4), ('备料组', '制作课', 3),
    ('材料课', None, 2), ('财务部', None, 4), ('生控部', None, 2), ('原料仓', '生控部', 7),
    ('供应链', None, 2), ('生产部', None, 4), ('手工组扫描', '生产部', 0),
    ('手工收料01', '手工组扫描', 0), ('手工收料02', '手工组扫描', 0),
    ('手工收料03', '手工组扫描', 10), ('裁断扫描', '生产部', 7),
    ('裁断收料01', '裁断扫描', 0), ('裁断收料02', '裁断扫描', 0),
    ('准备收料03', '裁断扫描', 0), ('准备收料04', '裁断扫描', 0),
    ('品管部', None, 11), ('行政部', None, 5), ('总经办', None, 2),
    ('离职组', None, 0), ('IT部', None, 0), ('多用途', None, 0), ('电商部', None, 0),
]

# 部门+人数（用 search_read 全量拉取，小数据量）
deps = rpc('hr.department', 'search_read', [[['name', 'in', [x[0] for x in ORG]]], ['id', 'name', 'parent_id']])
dep_map = {d['name']: d for d in deps}
emps = rpc('hr.employee', 'search_read', [[['department_id', 'in', [d['id'] for d in deps]]], ['name', 'department_id']])
cnt = {}
for e in emps:
    did = e['department_id'][0]
    cnt[did] = cnt.get(did, 0) + 1

bad = 0
print('%-14s %-14s %s' % ('部门', '上级', '人数'))
for name, parent, expect in ORG:
    d = dep_map.get(name)
    if not d:
        print('%-14s ✗ 缺失!' % name)
        bad += 1
        continue
    actual = cnt.get(d['id'], 0)
    pname = d['parent_id'][1] if d['parent_id'] else '-'
    # 校验父部门
    parent_ok = (pname == parent) if parent else (d['parent_id'] is False or pname == '-')
    ok = (actual == expect) and parent_ok
    if not ok:
        bad += 1
    print('%-14s %-14s %d/%d %s' % (name, pname if d['parent_id'] else '-', actual, expect, '✓' if ok else '✗'))

total_emps = rpc('hr.employee', 'search_count', [[]])
no_dep = rpc('hr.employee', 'search_count', [[['department_id', '=', False]]])
print('\n员工总数: %d | 未分配部门: %d | 异常项: %d' % (total_emps, no_dep, bad))
print('结论:', '全部正确 ✓' if bad == 0 else '存在异常 ✗')
