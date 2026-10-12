#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""远程 UI 验证：关键视图加载 + 菜单可见性"""
import json
import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'

s = requests.Session()


def call_kw(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}},
    }, timeout=120)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


# 登录
r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']
print('登录 uid:', uid)

# 1. 动态模型视图加载（get_views 会做完整 arch 校验）
for model in ['x_qc_inspection', 'x_qc_ncr', 'x_plm_eco']:
    v = call_kw(model, 'get_views', [[], {
        'form': [[False, 'form']], 'list': [[False, 'list']], 'search': [[False, 'search']],
    }])
    keys = list(v.keys())
    n = sum(1 for k in keys if k in ('form', 'list', 'search'))
    print('%s 视图加载 OK: %d 个视图' % (model, n))

# 2. 标准模块关键模型
for model in ['mrp.production', 'mrp.workorder', 'stock.picking', 'sale.order', 'purchase.order',
              'hr.attendance', 'hr.leave', 'hr.expense', 'project.project']:
    try:
        call_kw(model, 'fields_get', [], {'attributes': ['string']})
        print('%s OK' % model)
    except Exception as e:
        print('%s FAIL: %s' % (model, str(e)[:120]))

# 3. 菜单加载（走 webclient 控制器）
r2 = s.post(HOST + '/web/webclient/load_menus', json={'jsonrpc': '2.0', 'params': {}}, timeout=60)
menus = r2.json()['result']
names = [m.get('name') for m in menus.values() if isinstance(m, dict)]
for want in ['质量管理', '研发管理', '制造', '库存', '销售', '采购', '考勤', '项目']:
    print('菜单 [%s]: %s' % (want, '可见 ✓' if want in names else '不可见 ✗'))

# 4. 示例检验单状态流转（server action）
ids = call_kw('x_qc_inspection', 'search', [[['x_state', '=', 'draft']]], {'limit': 1})
if ids:
    # 找“开始检验” action 并执行
    acts = call_kw('ir.actions.server', 'search_read',
                   [[['name', '=', '检验单：开始检验']]], {'fields': ['id'], 'limit': 1})
    if acts:
        call_kw('ir.actions.server', 'run', [[acts[0]['id']]], {'active_id': ids[0], 'active_ids': [ids[0]], 'active_model': 'x_qc_inspection'})
        rec = call_kw('x_qc_inspection', 'read', [[ids[0]]], {'fields': ['x_state', 'x_name']})
        print('状态流转: %s => %s ✓' % (rec[0]['x_name'], rec[0]['x_state']))
        # 改回 draft 保留示例
        call_kw('x_qc_inspection', 'write', [[ids[0]], {'x_state': 'draft'}])

print('=== 远程 UI 验证完成 ===')
