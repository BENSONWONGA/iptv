#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""鞋企 ERP 现状审计：已装模块、主数据、流程配置"""
import json

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=300):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        return {'ERROR': str(d['error'])[:150]}
    return d['result']


a = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
print('登录:', 'OK' if a.json().get('result', {}).get('uid') else 'FAIL')

# ===== 1. 核心模块安装状态 =====
CORE = ['sale_management', 'purchase', 'mrp', 'mrp_plm', 'stock', 'quality_control', 'account',
        'hr', 'hr_expense', 'crm', 'project', 'website_sale', 'pos_sale', 'mrp_subcontracting',
        'stock_barcode', 'mrp_workorder', 'plm_shoe' , 'shoe_plm', 'shoe_qms', 'shoe_theme',
        'mrp_bom_version', 'quality_control_spreadsheet', 'stock_landed_costs']
mods = rpc('ir.module.module', 'search_read', [[['name', 'in', CORE]]], {'fields': ['name', 'state']})
states = {m['name']: m['state'] for m in mods}
print('\n===== 1. 核心模块 =====')
for m in CORE:
    print('  %-28s %s' % (m, states.get(m, '(不存在)')))

# ===== 2. 主数据统计 =====
print('\n===== 2. 主数据 =====')
for model, label in [
        ('product.template', '产品模板'), ('product.product', '产品变体'),
        ('product.category', '产品分类'), ('res.partner', '业务伙伴'),
        ('mrp.bom', '物料清单 BOM'), ('mrp.workcenter', '工作中心'),
        ('mrp.routing.workcenter', '工序'), ('stock.warehouse', '仓库'),
        ('stock.location', '库位'), ('hr.employee', '员工'),
        ('res.company', '公司'), ('uom.uom', '计量单位')]:
    cnt = rpc(model, 'search_count', [[]])
    print('  %-14s (%s): %s' % (label, model, cnt if isinstance(cnt, int) else cnt))

# ===== 3. 业务单据流转情况 =====
print('\n===== 3. 业务单据 =====')
for model, label, domain in [
        ('sale.order', '销售订单', []),
        ('purchase.order', '采购订单', []),
        ('mrp.production', '制造订单', []),
        ('stock.picking', '库存调拨', []),
        ('account.move', '会计分录', []),
        ('mrp.eco', 'PLM变更单', []),
        ('quality.alert', '质量警报', []),
        ('quality.check', '质量检验', [])]:
    try:
        cnt = rpc(model, 'search_count', [domain])
        print('  %-10s (%s): %s' % (label, model, cnt if isinstance(cnt, int) else cnt))
    except Exception as e:
        print('  %-10s (%s): 不可用 %s' % (label, model, str(e)[:60]))

# ===== 4. 工作中心/工序（制鞋产线） =====
print('\n===== 4. 制鞋产线配置 =====')
wcs = rpc('mrp.workcenter', 'search_read', [[]], {'fields': ['name', 'costs_hour', 'capacity', 'time_efficiency'], 'limit': 20})
if isinstance(wcs, list):
    print('  工作中心 (%d):' % len(wcs))
    for w in wcs:
        print('    - %s (¥%s/时)' % (w['name'], w.get('costs_hour')))
ops = rpc('mrp.routing.workcenter', 'search_read', [[]], {'fields': ['name', 'workcenter_id'], 'limit': 20})
if isinstance(ops, list):
    print('  工序 (%d):' % len(ops))
    for o in ops:
        print('    - %s @ %s' % (o['name'], o.get('workcenter_id', [0, ''])[1] if o.get('workcenter_id') else '-'))

# ===== 5. BOM 示例（是否配置了鞋料结构） =====
print('\n===== 5. BOM 结构示例 =====')
boms = rpc('mrp.bom', 'search_read', [[]], {'fields': ['code', 'product_tmpl_id', 'bom_line_ids', 'operation_ids', 'type'], 'limit': 5})
if isinstance(boms, list):
    for b in boms:
        print('  BOM %s: %s | 组件行 %d | 工序 %d | 类型 %s' % (
            b.get('code') or '-', b['product_tmpl_id'][1] if b.get('product_tmpl_id') else '-',
            len(b.get('bom_line_ids', [])), len(b.get('operation_ids', [])), b.get('type')))

# ===== 6. 自定义模块视图（鞋企 PLM/QMS） =====
print('\n===== 6. 自定义鞋企模块 =====')
for mod in ['shoe_plm', 'shoe_qms']:
    st = states.get(mod, '未安装')
    print('  %s: %s' % (mod, st))

# ===== 7. 用户与权限组 =====
print('\n===== 7. 用户 =====')
users = rpc('res.users', 'search_read', [[['active', '=', True]]], {'fields': ['login', 'name', 'groups_id'], 'limit': 30})
if isinstance(users, list):
    print('  活跃用户 (%d):' % len(users))
    for u in users[:15]:
        print('    - %s (%s) 组数=%d' % (u['name'], u['login'], len(u.get('groups_id', []))))
