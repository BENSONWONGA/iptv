#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复：清理被误标为供应商/客户的员工通讯录联系人
规则：
- 供应商：仅保留公司型名称（含 公司/厂/集团/实业/商行 等）
- 客户：保留公司型名称（排除自己公司）+ 有真实销售订单的伙伴
- 其余个人联系人：supplier_rank / customer_rank 清零（通讯录保留）
"""
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

COMPANY_KW = ['公司', '厂', '集团', '实业', '商行', '经营部', '门市部', '工作室', '中心', '有限公司']
own = rpc('res.company', 'search_read', [[]], {'fields': ['partner_id']})[0]
own_pid = own['partner_id'][0]

# 有真实单据引用的伙伴（不可清）
so_parts = set(x['partner_id'][0] for x in rpc('sale.order', 'search_read', [[]], {'fields': ['partner_id']}))
po_parts = set(x['partner_id'][0] for x in rpc('purchase.order', 'search_read', [[]], {'fields': ['partner_id']}))
print('真实订单引用: 销售客户 %s 个, 采购供应商 %s 个' % (len(so_parts), len(po_parts)))


def is_company(name):
    return any(k in name for k in COMPANY_KW)


# ===== 供应商清理 =====
print('===== 供应商清理 =====')
sups = rpc('res.partner', 'search_read', [[['supplier_rank', '>', 0]]],
           {'fields': ['name', 'supplier_rank']})
keep, clear = [], []
for p in sups:
    if p['id'] in po_parts or is_company(p['name']):
        keep.append(p)
    else:
        clear.append(p)
if clear:
    rpc('res.partner', 'write', [[p['id'] for p in clear], {'supplier_rank': 0}])
print('  保留供应商 %d 家: %s' % (len(keep), [p['name'] for p in keep]))
print('  清除误标 %d 人: %s ...' % (len(clear), [p['name'] for p in clear[:6]]))

# ===== 客户清理 =====
print('===== 客户清理 =====')
custs = rpc('res.partner', 'search_read', [[['customer_rank', '>', 0]]],
            {'fields': ['name', 'customer_rank']})
keep_c, clear_c = [], []
for p in custs:
    if p['id'] == own_pid:
        clear_c.append(p)  # 自己公司不算客户
    elif p['id'] in so_parts or is_company(p['name']):
        keep_c.append(p)
    else:
        clear_c.append(p)
if clear_c:
    rpc('res.partner', 'write', [[p['id'] for p in clear_c], {'customer_rank': 0}])
print('  保留客户 %d 个: %s' % (len(keep_c), [p['name'] for p in keep_c]))
print('  清除误标/自公司 %d 个: %s ...' % (len(clear_c), [p['name'] for p in clear_c[:6]]))

# ===== 验证 =====
print('\n===== 验证 =====')
n_sup = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0]]])
n_cust = rpc('res.partner', 'search_count', [[['customer_rank', '>', 0]]])
print('  供应商列表: %d 家' % n_sup)
for p in rpc('res.partner', 'search_read', [[['supplier_rank', '>', 0]]], {'fields': ['name']}):
    print('    - %s' % p['name'])
print('  客户列表: %d 个' % n_cust)
for p in rpc('res.partner', 'search_read', [[['customer_rank', '>', 0]]], {'fields': ['name']}):
    print('    - %s' % p['name'])
print('  通讯录（全部联系人）: %s 条（不变，员工联系人保留）' % rpc('res.partner', 'search_count', [[]]))
