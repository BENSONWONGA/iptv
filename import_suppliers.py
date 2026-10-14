#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导入供应商.xlsx → Odoo res.partner（供应商）
- 供应商名 → 名称（公司类型，supplier_rank=1）
- 付款方式 → 付款条款（复用客户导入建的 + 新建月结120天/货到付款）
- 厂商类型 → res.partner.category 标签
- 地址 → 供应商 street；币别/税点 → 内部备注
- 联系人+电话 → 子联系人（无联系人但有电话 → 电话放供应商上）
- 批量 create 提速（50条/批）
"""
import json

import pandas as pd
import requests

HOST = 'http://220.162.99.166:9000'
XLSX = '/workspace/.uploads/0d978279-fabb-43ea-8c5f-8228dac4a6a4_供应商.xlsx'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'params': {'model': model, 'method': method,
                                     'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


def clean(v):
    """NaN 安全清洗"""
    if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
        return ''
    return str(v).strip()


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

# ===== 1. 读数据 =====
df = pd.read_excel(XLSX)
df.columns = [str(c).strip() for c in df.columns]
df = df[df['供应商名'].notna()]
df = df[df['供应商名'].astype(str).str.strip().str.len() > 3]  # 去掉"864"这类垃圾行
print('有效供应商: %d 条' % len(df))

# ===== 2. 付款条款 =====
PT_MAP = {
    '对公转账': '对公转账',
    '现金': '现金付款',
    '汇款月结30天': '月结30天',
    '汇款月结60天': '月结60天',
    '汇款月结90天': '月结90天',
    '汇款月结120天': '月结120天',
    '款到发货现金': '款到发货（现金）',
    '货到付款现金': '货到付款（现金）',
}
DAYS = {'月结30天': 30, '月结60天': 60, '月结90天': 90, '月结120天': 120}
term_ids = {}
for src, name in PT_MAP.items():
    ex = rpc('account.payment.term', 'search_read', [[['name', '=', name]]], {'fields': ['id']})
    if ex:
        term_ids[src] = ex[0]['id']
    else:
        days = DAYS.get(name, 0)
        term_ids[src] = rpc('account.payment.term', 'create', [{
            'name': name,
            'line_ids': [(0, 0, {'value': 'percent', 'value_amount': 100.0,
                                 'nb_days': days, 'delay_type': 'days_after'})],
        }])
print('付款条款: %s' % term_ids)

# ===== 3. 厂商类型 → 标签 =====
types = sorted({clean(v) for v in df['厂商类型'] if clean(v)})
tag_ids = {}
for tname in types:
    ex = rpc('res.partner.category', 'search_read', [[['name', '=', tname]]], {'fields': ['id']})
    if ex:
        tag_ids[tname] = ex[0]['id']
    else:
        tag_ids[tname] = rpc('res.partner.category', 'create', [{'name': tname}])
print('厂商类型标签: %s' % tag_ids)

# ===== 4. 已有供应商（避免与 3 家重复）=====
existing = {p['name']: p['id'] for p in rpc(
    'res.partner', 'search_read', [[['supplier_rank', '>', 0]]], {'fields': ['name']})}
print('已有供应商: %s' % list(existing))

# ===== 5. 批量创建供应商 =====
print('===== 创建供应商 =====')
to_create = []
skip_existing = 0
for _, row in df.iterrows():
    name = clean(row['供应商名'])
    if name in existing:
        skip_existing += 1
        continue
    cur, tax, pay = clean(row['币别']), clean(row['税点']), clean(row['付款方式'])
    addr, mtype = clean(row['地址']), clean(row['厂商类型'])
    contact, phone = clean(row['联 系 人']), clean(row['联系电话']).replace('?', '-').replace(' ', '')
    comment = '导入自旧系统厂商档案'
    if cur:
        comment += '；币别: %s' % cur
    if tax:
        comment += '；税点: %s' % tax
    if pay:
        comment += '；原付款方式: %s' % pay
    vals = {'name': name, 'is_company': True, 'supplier_rank': 1, 'comment': comment}
    if addr:
        vals['street'] = addr
    if pay in term_ids:
        vals['property_supplier_payment_term_id'] = term_ids[pay]
    if mtype and mtype in tag_ids:
        vals['category_id'] = [(4, tag_ids[mtype])]
    # 无联系人但有电话 → 电话挂供应商
    if not contact and phone:
        vals['phone'] = phone
    to_create.append((name, vals, contact, phone))

print('  待创建: %d | 跳过同名: %d' % (len(to_create), skip_existing))
name2id = {}
BATCH = 50
for i in range(0, len(to_create), BATCH):
    chunk = to_create[i:i + BATCH]
    ids = rpc('res.partner', 'create', [[v for _, v, _, _ in chunk]])
    if isinstance(ids, int):
        ids = [ids]
    for (name, _, _, _), pid in zip(chunk, ids):
        name2id[name] = pid
    if (i // BATCH + 1) % 4 == 0:
        print('  进度: %d/%d' % (min(i + BATCH, len(to_create)), len(to_create)))
print('  创建完成: %d 家' % len(name2id))

# ===== 6. 批量创建子联系人 =====
print('===== 创建子联系人 =====')
ctc = []
for name, vals, contact, phone in to_create:
    if not contact or name not in name2id:
        continue
    cv = {'name': contact, 'parent_id': name2id[name], 'type': 'contact'}
    if phone:
        cv['phone'] = phone
    ctc.append(cv)
n_sub = 0
for i in range(0, len(ctc), BATCH):
    chunk = ctc[i:i + BATCH]
    rpc('res.partner', 'create', [chunk])
    n_sub += len(chunk)
print('  子联系人: %d 个' % n_sub)

# ===== 7. 验证 =====
print('===== 验证 =====')
n_sup = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0]]])
n_pt = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0], ['property_supplier_payment_term_id', '!=', False]]])
n_addr = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0], ['street', '!=', False]]])
n_usd = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0], ['comment', 'like', 'USD']]])
n_sub_v = rpc('res.partner', 'search_count', [[['parent_id', '!=', False], ['type', '=', 'contact'], ['parent_id.supplier_rank', '>', 0]]])
print('  供应商总数: %s（预期 864 + 3 原 = 867）' % n_sup)
print('  关联付款条款: %s | 有地址: %s | USD: %s | 子联系人: %s' % (n_pt, n_addr, n_usd, n_sub_v))
# 标签统计
for tname, tid in tag_ids.items():
    cnt = rpc('res.partner', 'search_count', [[['supplier_rank', '>', 0], ['category_id', 'in', [tid]]]])
    print('  标签[%s]: %d 家' % (tname, cnt))
# 抽样
samples = rpc('res.partner', 'search_read', [[['supplier_rank', '>', 0], ['name', 'like', '恒得利']],
                                             ['name', 'like', '中鼎']],
              {'fields': ['name', 'street', 'category_id', 'property_supplier_payment_term_id']})
for p in samples:
    pt = p['property_supplier_payment_term_id'][1] if p.get('property_supplier_payment_term_id') else '-'
    cats = [c[1] for c in p.get('category_id', [])] or '-'
    print('  抽样: %s | %s | %s | %s' % (p['name'], cats, pt, (p.get('street') or '-')[:20]))
print('=== 导入完成 ===')
