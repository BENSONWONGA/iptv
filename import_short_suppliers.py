#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补导 17 条短名称供应商 + 最终核验"""
import json

import pandas as pd
import requests

HOST = 'http://220.162.99.166:9000'
XLSX = '/workspace/.uploads/0d978279-fabb-43ea-8c5f-8228dac4a6a4_供应商.xlsx'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=300):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'params': {'model': model, 'method': method,
                                     'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:250])
    return d['result']


def clean(v):
    if v is None or pd.isna(v):
        return ''
    return str(v).strip()


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

df = pd.read_excel(XLSX)
df.columns = [str(c).strip() for c in df.columns]
df = df[df['供应商名'].notna()]
names = df['供应商名'].astype(str).str.strip()
short_df = df[names.str.len() <= 3]

SKIP = {'864', '奥登科'}  # 垃圾行 + 自己公司
created, dual, skipped = 0, 0, []
for _, row in short_df.iterrows():
    name = clean(row['供应商名'])
    if name in SKIP:
        skipped.append(name)
        continue
    cur, tax, pay = clean(row['币别']), clean(row['税点']), clean(row['付款方式'])
    contact, phone = clean(row['联 系 人']), clean(row['联系电话']).replace('?', '-')
    comment = '导入自旧系统厂商档案（短名称）'
    if cur:
        comment += '；币别: %s' % cur
    if tax:
        comment += '；税点: %s' % tax
    # 同名已有伙伴（如客户）→ 加供应商角色
    ex = rpc('res.partner', 'search_read', [[['name', '=', name]]],
             {'fields': ['id', 'customer_rank']})
    if ex:
        rpc('res.partner', 'write', [[ex[0]['id']], {'supplier_rank': 1}])
        dual += 1
        print('  双角色: %s（原客户，现为客户+供应商）' % name)
        continue
    vals = {'name': name, 'is_company': True, 'supplier_rank': 1, 'comment': comment}
    pid = rpc('res.partner', 'create', [vals])
    if contact and contact != name:
        rpc('res.partner', 'create', [{'name': contact, 'parent_id': pid,
                                       'type': 'contact', 'phone': phone}])
    elif phone:
        rpc('res.partner', 'write', [[pid], {'phone': phone}])
    created += 1
    print('  创建: %s' % name)

print('补导: 新建 %d | 双角色 %d | 跳过 %s' % (created, dual, skipped))

# ===== 最终核验 =====
print('\n===== 供应商导入最终核验 =====')
n_sup = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0]]])
n_pt = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0], ['property_supplier_payment_term_id', '!=', False]]])
n_addr = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0], ['street', '!=', False]]])
n_sub = rpc('res.partner', 'search_count', [[['parent_id', '!=', False], ['type', '=', 'contact'], ['parent_id.supplier_rank', '>', 0]]])
n_both = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0], ['customer_rank', '>', 0]]])
print('  供应商总数: %s（846 + 17 = 863，不含 3 家已归档测试供应商）' % n_sup)
print('  关联付款条款: %s | 有地址: %s | 子联系人: %s | 客供双角色: %s' % (n_pt, n_addr, n_sub, n_both))
EOF_MARKER = True
