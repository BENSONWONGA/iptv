#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补建 33 个失败的子联系人（NaN 电话导致 JSON 序列化失败）"""
import json

import pandas as pd
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=300):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'params': {'model': model, 'method': method,
                                     'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:200])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

df = pd.read_excel('/workspace/.uploads/c7277b84-768b-4284-9f18-5f3b50544dfc_客户档案.xlsx')
df.columns = [str(c).strip() for c in df.columns]
df = df[df['客户名称'].notna() & df['财务代号'].notna()]

created, exist = 0, 0
for _, row in df.iterrows():
    contact = row.get('联系人')
    if pd.isna(contact) or not str(contact).strip():
        continue
    contact = str(contact).strip()
    phone_raw = row.get('联系电话')
    phone = '' if pd.isna(phone_raw) else str(phone_raw).strip().replace('?', '-').replace(' ', '')

    # 找客户（按财务代号 ref）
    cust = rpc('res.partner', 'search_read',
               [[['ref', '=', str(row['财务代号']).strip()], ['customer_rank', '>', 0]]],
               {'fields': ['id', 'name']})
    if not cust:
        print('✗ 找不到客户: %s' % row['客户名称'])
        continue
    pid = cust[0]['id']
    # 子联系人是否已存在
    cex = rpc('res.partner', 'search_read',
              [[['name', '=', contact], ['parent_id', '=', pid]]], {'fields': ['id']})
    if cex:
        exist += 1
        continue
    vals = {'name': contact, 'parent_id': pid, 'type': 'contact'}
    if phone:
        vals['phone'] = phone
    rpc('res.partner', 'create', [vals])
    created += 1

print('补建子联系人: %d 个（已存在 %d 个）' % (created, exist))

# ===== 最终验证 =====
print('===== 最终验证 =====')
n_cust = rpc('res.partner', 'search_count', [[['customer_rank', '>', 0]]])
n_sub = rpc('res.partner', 'search_count', [[['parent_id', '!=', False], ['type', '=', 'contact']]])
n_ref = rpc('res.partner', 'search_count', [[['customer_rank', '>', 0], ['ref', '!=', False]]])
n_pt = rpc('res.partner', 'search_count', [[['customer_rank', '>', 0], ['property_payment_term_id', '!=', False]]])
print('客户总数: %s（预期 132 = 131 新 + 曾春香）' % n_cust)
print('带财务代号: %s | 关联付款条款: %s' % (n_ref, n_pt))
print('客户子联系人: %s（预期 73）' % n_sub)

# 检查之前多出的 1 个客户
print('\n排查客户列表中的非导入项:')
extras = rpc('res.partner', 'search_read',
             [[['customer_rank', '>', 0], ['ref', '=', False]]], {'fields': ['name']})
for p in extras:
    print('  - %s（无财务代号）' % p['name'])
