#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补充审计：会计/税务/日记账、销售配置、库存规则"""
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=300):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        return {'ERROR': str(d['error'])[:120]}
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

print('===== 8. 会计配置 =====')
jr = rpc('account.journal', 'search_read', [[]], {'fields': ['name', 'type', 'code']})
if isinstance(jr, list):
    print('  日记账 (%d):' % len(jr))
    for j in jr:
        print('    - %s [%s] %s' % (j['name'], j['type'], j.get('code') or ''))
taxes = rpc('account.tax', 'search_read', [[]], {'fields': ['name', 'amount', 'type_tax_use'], 'limit': 15})
if isinstance(taxes, list):
    print('  税率 (%d):' % len(taxes))
    for t in taxes[:8]:
        print('    - %s %s%% (%s)' % (t['name'], t['amount'], t['type_tax_use']))
else:
    print('  税率:', taxes)
accs = rpc('account.account', 'search_count', [[]])
print('  会计科目数:', accs if isinstance(accs, int) else accs)
pos = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0]]])
cust = rpc('res.partner', 'search_count', [[['customer_rank', '>', 0]]])
print('  供应商数: %s | 客户数: %s' % (pos if isinstance(pos, int) else pos, cust if isinstance(cust, int) else cust))

print('===== 9. 库存补货规则 =====')
rules = rpc('stock.warehouse.orderpoint', 'search_count', [[]])
print('  再订货规则:', rules if isinstance(rules, int) else rules)
routes = rpc('stock.route', 'search_read', [[['warehouse_selectable', '=', True]]], {'fields': ['name']})
print('  可选路由:', [r['name'] for r in routes] if isinstance(routes, list) else routes)

print('===== 10. 产品明细抽样 =====')
prods = rpc('product.template', 'search_read', [[['type', '!=', 'service']]],
            {'fields': ['name', 'categ_id', 'type', 'purchase_ok', 'sale_ok', 'is_storable'], 'limit': 40})
if isinstance(prods, list):
    fg = [p for p in prods if p.get('sale_ok')]
    mat = [p for p in prods if p.get('purchase_ok') and not p.get('sale_ok')]
    print('  抽样 %d 个：可售 %d / 采购件 %d' % (len(prods), len(fg), len(mat)))
    cats = {}
    for p in prods:
        cn = p['categ_id'][1] if p.get('categ_id') else '无'
        cats[cn] = cats.get(cn, 0) + 1
    print('  分类分布:', cats)

print('===== 11. 权限组（鞋企角色） =====')
groups = rpc('res.groups', 'search_read', [[['name', 'ilike', '鞋']], [['category_id.name', 'ilike', '鞋']],
                                           [['full_name', 'ilike', 'shoe']]], {'fields': ['name', 'full_name']})
print('  鞋企相关组:', groups if isinstance(groups, list) else groups)
