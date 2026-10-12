#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 admin 加入各业务模块管理组，确保菜单可见"""
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
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']

# 各模块管理组 xmlid
GROUPS = [
    ('销售', 'sales_team.group_sale_manager'),
    ('采购', 'purchase.group_purchase_manager'),
    ('制造/MES', 'mrp.group_mrp_manager'),
    ('工单工艺', 'mrp.group_mrp_routings'),
    ('批次', 'stock.group_production_lot'),
    ('库存/WMS', 'stock.group_stock_manager'),
    ('多库位', 'stock.group_stock_multi_locations'),
    ('考勤', 'hr_attendance.group_hr_attendance_officer'),
    ('休假', 'hr_holidays.group_hr_holidays_manager'),
    ('费用', 'hr_expense.group_hr_expense_manager'),
    ('工时', 'hr_timesheet.group_hr_timesheet_approver'),
    ('项目', 'project.group_project_manager'),
    ('财务会计', 'account.group_account_manager'),
    ('质量/技术员', 'quality.group_quality_control_user'),  # 可能不存在
]

for label, xmlid in GROUPS:
    try:
        gid = call_kw('ir.model.data', 'xmlid_to_res_id', [xmlid], {'raise_if_not_found': False})
        if not gid or gid is True:
            print('  跳过 %s (%s 不存在)' % (label, xmlid))
            continue
        call_kw('res.groups', 'write', [[gid], {'users': [(4, uid)]}])
        print('  ✓ %s => 组 id %s' % (label, gid))
    except Exception as e:
        print('  ✗ %s: %s' % (label, str(e)[:100]))

# 重新验证菜单
menus = call_kw('ir.ui.menu', 'search_read',
                [[['parent_id', '=', False]]], {'fields': ['name'], 'limit': 100})
names = [m['name'] for m in menus]
print('顶级菜单:', names)
