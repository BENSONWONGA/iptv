#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按组织架构图录入部门与人员到 Odoo 20 (hr模块)"""
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=600)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
uid = r.json()['result']['uid']
print('RPC 登录 ✓ uid=%s' % uid)

# ── 0. 检查 hr 模块 ──────────────────────────────
models = rpc('ir.model', 'search_read', [[['model', 'in', ['hr.department', 'hr.employee']]], ['model']])
have = {m['model'] for m in models}
if 'hr.employee' not in have:
    print('hr 未安装，安装中...')
    ids = rpc('ir.module.module', 'search', [[['name', '=', 'hr']]])
    assert ids, 'hr 模块未找到'
    rpc('ir.module.module', 'button_immediate_install', [ids])
    print('hr 已安装 ✓')
else:
    print('hr 已安装 ✓')

# ── 1. 组织架构数据 ──────────────────────────────
# 结构：(部门名, 父部门名 or None, [人员...])
ORG = [
    ('业务部', None, ['傅新新', '曾春香']),
    ('大货业务', '业务部', ['林其堂', '胡晓霞', '曾巧云']),
    ('样品开发', '业务部', ['郭婷婷', '戴丽萍', '江远琴', '魏根华', '汪宝丽', '尹巧如', '吴俊杰', '汪建安', '唐建标']),
    ('开发部', None, ['林养三']),
    ('开发室01', '开发部', []),
    ('技转课', '开发室01', ['许丽萍', '陈凤飞', '盘贤平', '曾现丰', '杨小勤']),
    ('开发设计课', '开发部', ['涂星财', '林桂旺', '郑彩玲', '肖北平', '黄祥鹏', '张荣', '彭洪念', '胡杨华', '蔡上华']),
    ('制作课', '开发部', ['李王乔', '陈俊杰', '曾凡军', '黄建华']),
    ('备料组', '制作课', ['郑彩霞', '陈丽萍', '李雪云']),
    ('材料课', None, ['许聪荣', '丁少林']),
    ('财务部', None, ['姚嫦娥', '李雅婷', '李紫姗', '张金元']),
    ('生控部', None, ['唐章明', '付宗令']),
    ('原料仓', '生控部', ['杨银平', '邓宣发', '郭辉', '彭钦茂', '罗朋景', '李义军', '郑荣善']),
    ('供应链', None, ['黄锦华', '曾广军']),
    ('生产部', None, ['皮尉梅', '郭火根', '杨钟琪', '夏萍']),
    ('手工组扫描', '生产部', []),
    ('手工收料01', '手工组扫描', []),
    ('手工收料02', '手工组扫描', []),
    ('手工收料03', '手工组扫描', ['马永琪', '张芬', '陈良旺', '王培彬', '郭德高', '谭斌', '胡秀霞', '黄通权', '吴凤琼', '荣琴']),
    ('裁断扫描', '生产部', ['文留柱', '王振南', '刘广容', '唐宗奎', '盛炳添', '张武平', '陈美荣']),
    ('裁断收料01', '裁断扫描', []),
    ('裁断收料02', '裁断扫描', []),
    ('准备收料03', '裁断扫描', []),
    ('准备收料04', '裁断扫描', []),
    ('品管部', None, ['薛莹秀', '贺平', '何春莲', '黄维苏', '林玉兰', '阮红淑', '林荣兰', '粟水莲', '何琼华', '刘莉莉', '赖传爱']),
    ('行政部', None, ['何瑞', '廖善鑫', '刘祖华', '程光华', '黄非凡']),
    ('总经办', None, ['陈一伟', '陈一雄']),
    ('离职组', None, []),
    ('IT部', None, []),
    ('多用途', None, []),
    ('电商部', None, []),
]
n_emp = sum(len(x[2]) for x in ORG)
print('计划：%d 个部门, %d 名员工' % (len(ORG), n_emp))

# ── 2. 创建部门（先父后子，查重防重跑）────────────
dep_ids = {}
existing_deps = rpc('hr.department', 'search_read', [[['name', 'in', [x[0] for x in ORG]]], ['id', 'name']])
for d in existing_deps:
    dep_ids[d['name']] = d['id']
print('已存在部门 %d 个' % len(dep_ids))

created_dep = 0
for name, parent, _emps in ORG:  # ORG 按父先子后顺序排列
    if name in dep_ids:
        continue
    vals = {'name': name}
    if parent:
        assert parent in dep_ids, '父部门缺失: %s' % parent
        vals['parent_id'] = dep_ids[parent]
    new_id = rpc('hr.department', 'create', [vals])
    dep_ids[name] = new_id
    created_dep += 1
print('新建部门 %d 个, 共 %d' % (created_dep, len(dep_ids)))

# ── 3. 创建员工（查重：同名+同部门）───────────────
existing_emps = rpc('hr.employee', 'search_read', [[['name', 'in', [n for _, _, es in ORG for n in es]]], ['id', 'name', 'department_id']])
have_set = {(e['name'], e['department_id'][0] if e['department_id'] else False) for e in existing_emps}
print('已存在同名员工 %d 个（将跳过部门相同的）' % len(existing_emps))

created_emp = 0
for name, parent, emps in ORG:
    for emp in emps:
        if (emp, dep_ids[name]) in have_set:
            continue
        rpc('hr.employee', 'create', [{'name': emp, 'department_id': dep_ids[name]}])
        created_emp += 1
print('新建员工 %d 个' % created_emp)

# ── 4. 验证 ─────────────────────────────────────
total_deps = rpc('hr.department', 'search_count', [[]])
total_emps = rpc('hr.employee', 'search_count', [[]])
print('验证：hr.department=%d, hr.employee=%d' % (total_deps, total_emps))

# 各部门人数
stats = rpc('hr.employee', 'read_group', [[[]], ['department_id'], ['department_id']], kwargs={'lazy': True})
stat_map = {r['department_id'][0]: r['department_id_count'] for r in stats if r['department_id']}
print('\n部门人员分布：')
for name, parent, emps in ORG:
    cnt = stat_map.get(dep_ids[name], 0)
    expect = len(emps)
    flag = '✓' if cnt == expect else '✗ 期望%d实际%d' % (expect, cnt)
    print('  %s%s: %d 人 %s' % ('  ' if parent else '', name, cnt, flag))

# 找出没挂部门的员工（应为 0）
no_dep = rpc('hr.employee', 'search_count', [[['department_id', '=', False]]])
print('\n未分配部门员工: %d' % no_dep)
print('\n完成 ✓')
