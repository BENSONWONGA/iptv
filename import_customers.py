#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入客户档案.xlsx → Odoo res.partner
- 客户名称+财务代号(ref) 为主档，is_company=True, customer_rank=1
- 付款方式 → 创建 Odoo 付款条款并关联
- 联系人+联系电话 → 子联系人（type=contact）
- 币别/单据状态 → 内部备注
- 同名已存在 → 更新而非重复创建
"""
import json

import pandas as pd
import requests

HOST = 'http://220.162.99.166:9000'
XLSX = '/workspace/.uploads/c7277b84-768b-4284-9f18-5f3b50544dfc_客户档案.xlsx'
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

# ===== 1. 读取并清洗数据 =====
df = pd.read_excel(XLSX)
df.columns = [str(c).strip() for c in df.columns]
df = df[df['客户名称'].notna() & df['财务代号'].notna()]  # 去掉垃圾行
for c in ['客户名称', '财务代号', '币别', '付款方式', '单据状态']:
    df[c] = df[c].astype(str).str.strip().replace({'nan': ''})
df['联系电话'] = df['联系电话'].astype(str).str.strip().replace({'nan': ''})
df['联系电话'] = df['联系电话'].str.replace('?', '-', regex=False).str.replace(' ', '', regex=False)
print('有效客户: %d 条' % len(df))

# ===== 2. 付款条款映射与创建 =====
print('===== 2. 付款条款 =====')
PT_MAP = {  # Excel付款方式 → (条款名, 账期天数)
    '对公转账': ('对公转账', 0),
    '汇款月结30天': ('月结30天', 30),
    '汇款月结50天': ('月结50天', 50),
    '汇款月结60天': ('月结60天', 60),
    '汇款月结90天': ('月结90天', 90),
    '承兑月结90天': ('承兑月结90天', 90),
    '款到发货现金': ('款到发货（现金）', 0),
    '现金': ('现金付款', 0),
    '见提单复印件付款': ('见提单复印件付款', 0),
}
term_ids = {}
for src, (name, days) in PT_MAP.items():
    ex = rpc('account.payment.term', 'search_read', [[['name', '=', name]]], {'fields': ['id']})
    if ex:
        term_ids[src] = ex[0]['id']
    else:
        tid = rpc('account.payment.term', 'create', [{
            'name': name,
            'line_ids': [(0, 0, {'value': 'percent', 'value_amount': 100.0,
                                 'nb_days': days, 'delay_type': 'days_after'})],
        }])
        term_ids[src] = tid
    print('  %-14s → %s (id=%s)' % (src, name, term_ids[src]))

# Odoo 自带立即付款备用
imm = rpc('account.payment.term', 'search_read', [[['name', 'in', ['Immediate', '立即付款', 'Immediate Payment']]]],
          {'fields': ['id', 'name']})
if imm:
    print('  内置立即付款: %s' % imm[0]['name'])

# ===== 3. 导入客户 =====
print('===== 3. 导入客户 =====')
created, updated, skipped = 0, 0, 0
err_rows = []
for _, row in df.iterrows():
    name = row['客户名称']
    ref = row['财务代号']
    cur = row['币别']
    pay = row['付款方式']
    status = row['单据状态']
    contact = str(row.get('联系人', '')).strip()
    if contact in ('nan', ''):
        contact = ''
    phone = row['联系电话']
    try:
        comment = '导入自旧系统客户档案'
        if cur:
            comment += '；币别: %s' % cur
        if pay:
            comment += '；原付款方式: %s' % pay
        if status:
            comment += '；原状态: %s' % status
        vals = {
            'customer_rank': 1,
            'ref': ref,
            'comment': comment,
        }
        if pay in term_ids:
            vals['property_payment_term_id'] = term_ids[pay]
        # 同名检查
        ex = rpc('res.partner', 'search_read', [[['name', '=', name]]], {'fields': ['id', 'customer_rank']})
        if ex:
            rpc('res.partner', 'write', [[ex[0]['id']], vals])
            pid = ex[0]['id']
            updated += 1
        else:
            vals.update({'name': name, 'is_company': True})
            pid = rpc('res.partner', 'create', [vals])
            created += 1
        # 子联系人
        if contact:
            cex = rpc('res.partner', 'search_read',
                      [[['name', '=', contact], ['parent_id', '=', pid]]], {'fields': ['id']})
            cv = {'phone': phone} if phone else {}
            if cex:
                if cv:
                    rpc('res.partner', 'write', [[cex[0]['id']], cv])
            else:
                cv.update({'name': contact, 'parent_id': pid, 'type': 'contact'})
                rpc('res.partner', 'create', [cv])
    except Exception as e:
        err_rows.append((name, str(e)[:100]))
        skipped += 1

print('  新建客户: %d' % created)
print('  更新已有: %d' % updated)
print('  失败: %d %s' % (skipped, err_rows[:5] if err_rows else ''))

# ===== 4. 子联系人统计 =====
sub_cnt = 0
for _, row in df.iterrows():
    pass  # 统计放验证里

# ===== 5. 验证 =====
print('===== 4. 验证 =====')
n_cust = rpc('res.partner', 'search_count', [[['customer_rank', '>', 0]]])
print('客户总数: %s（含原曾春香 = 131+1=132 预期）' % n_cust)
# ref 检查
with_ref = rpc('res.partner', 'search_count', [[['customer_rank', '>', 0], ['ref', '!=', False]]])
print('带财务代号的客户: %s' % with_ref)
# 付款条款检查
n_pt = rpc('account.payment.term', 'search_count', [[]])
print('付款条款总数: %s' % n_pt)
# 抽样
samples = rpc('res.partner', 'search_read',
              [[['ref', 'in', ['C001', 'C002', 'C210']]]],
              {'fields': ['name', 'ref', 'property_payment_term_id', 'comment']})
for p in samples:
    pt = p['property_payment_term_id'][1] if p.get('property_payment_term_id') else '-'
    print('  抽样 %s(%s): 付款条款=%s' % (p['name'], p['ref'], pt))
# 子联系人抽样
subs = rpc('res.partner', 'search_read',
           [[['parent_id', '!=', False], ['type', '=', 'contact'], ['phone', '!=', False]]],
           {'fields': ['name', 'phone', 'parent_id'], 'limit': 5})
print('  带电话的子联系人样例:')
for c in subs:
    print('    %s (%s) ← %s' % (c['name'], c['phone'], c['parent_id'][1]))
print('=== 导入完成 ===')
