#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试 get_views 返回结构 + load_menus"""
import json
import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'

s = requests.Session()

r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']
print('uid:', uid, 'cookies:', list(s.cookies.keys()))


def call_kw(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}},
    }, timeout=120)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


# get_view 逐类型验证（会做完整 arch 校验和视图继承组合）
for model in ['x_qc_inspection', 'x_qc_ncr', 'x_plm_eco']:
    for vt in ['form', 'list', 'search']:
        v = call_kw(model, 'get_view', [], {'view_id': False, 'view_type': vt})
        arch = v.get('arch', '')
        print('%s [%s] OK, arch %d 字节, 字段数 %d' % (model, vt, len(arch), len(v.get('fields', {}))))

# 菜单可见性（模拟 webclient 权限过滤）
menus = call_kw('ir.ui.menu', 'search_read',
                [[['parent_id', '=', False]]], {'fields': ['name'], 'limit': 100})
names = [m['name'] for m in menus]
print('菜单总数:', len(names))
for want in ['质量管理', '研发管理', '制造', '库存', '销售', '采购', '考勤', '休假', '费用', '项目', '工单']:
    print('  [%s]: %s' % (want, '可见' if want in names else '不可见'))
