#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据补全：
1. 检查 l10n_cn 中国本地化并安装（含13%税率+中文科目）
2. 给所有成品鞋补 BOM（克隆现有 BOM 结构）
3. 业务伙伴赋角色（供应商/客户）
4. 再订货规则（材料自动补货）
"""
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=900):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

# ===== 1. 中国本地化 =====
print('===== 1. 中国本地化 =====')
m = rpc('ir.module.module', 'search_read', [[['name', '=', 'l10n_cn']]], {'fields': ['name', 'state']})
if m:
    print('l10n_cn: %s' % m[0]['state'])
    if m[0]['state'] != 'installed':
        rpc('ir.module.module', 'button_immediate_install', [[m[0]['id']]])
        print('l10n_cn 安装完成（含中国税率+会计科目）')
else:
    print('l10n_cn 不存在（社区版内置应存在）')

# 装完本地化后重新登录（公司会计科目可能变化）
s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

# ===== 2. BOM 补齐 =====
print('===== 2. BOM 补齐 =====')
# 成品鞋分类下的产品
cats = rpc('product.category', 'search_read', [[['name', '=', '成品鞋']]], {'fields': ['id']})
if cats:
    cat_id = cats[0]['id']
    fgs = rpc('product.template', 'search_read', [[['categ_id', '=', cat_id]]],
              {'fields': ['name', 'default_code']})
    print('成品鞋模板 (%d):' % len(fgs))
    have, miss = [], []
    for p in fgs:
        boms = rpc('mrp.bom', 'search_read', [[['product_tmpl_id', '=', p['id']]]], {'fields': ['code']})
        (have if boms else miss).append(p)
    print('  已有 BOM: %d %s' % (len(have), [p['name'][:12] for p in have]))
    print('  缺 BOM: %d %s' % (len(miss), [p['name'][:12] for p in miss]))

    if have and miss:
        src = have[0]
        src_bom = rpc('mrp.bom', 'search_read', [[['product_tmpl_id', '=', src['id']]]],
                      {'fields': ['id', 'code']})[0]
        for p in miss:
            new_id = rpc('mrp.bom', 'copy', [[src_bom['id']]],
                         {'default_product_tmpl_id': p['id']})
            rpc('mrp.bom', 'write', [[new_id], {'code': 'BOM-%s' % (p.get('default_code') or p['id'])}])
            print('  ✓ %s → BOM-%s' % (p['name'][:20], p.get('default_code') or p['id']))

# 验证 BOM 总数
nb = rpc('mrp.bom', 'search_count', [[]])
print('BOM 总数: %s' % nb)

# ===== 3. 业务伙伴角色 =====
print('===== 3. 业务伙伴角色 =====')
partners = rpc('res.partner', 'search_read', [[['supplier_rank', '=', 0], ['customer_rank', '=', 0],
                                               ['name', 'not in', ['OdooBot', 'My Company (San Francisco)', 'Administrator']]]],
               {'fields': ['name'], 'limit': 100})
sup_kw = ['皮业', '皮革', '纺织', '布业', '鞋材', '化工', '贸易', '材料', '辅料', '底业', '橡胶', '胶水', '五金']
cust_kw = ['鞋业', '商贸', '商城', '百货', '店铺', '专卖店', '体育', '户外']
sup_ids, cust_ids = [], []
for p in partners:
    n = p['name']
    if any(k in n for k in sup_kw):
        sup_ids.append(p['id'])
    elif any(k in n for k in cust_kw):
        cust_ids.append(p['id'])
# 剩余的按顺序补足
rest = [p['id'] for p in partners if p['id'] not in sup_ids + cust_ids]
half = len(rest) // 3
sup_ids += rest[:half]
cust_ids += rest[half:half * 2]
if sup_ids:
    rpc('res.partner', 'write', [sup_ids, {'supplier_rank': 1}])
if cust_ids:
    rpc('res.partner', 'write', [cust_ids, {'customer_rank': 1}])
print('标记供应商: %d 家, 客户: %d 家' % (len(sup_ids), len(cust_ids)))

# ===== 4. 税率修正（若 l10n_cn 未生效则手工改） =====
print('===== 4. 税率 =====')
taxes = rpc('account.tax', 'search_read', [[]], {'fields': ['name', 'amount', 'type_tax_use']})
print('当前税率:', [(t['name'], t['amount']) for t in taxes[:8]])
if not any('13' in str(t['amount']) for t in taxes):
    # 手工改 15% → 13%
    for t in taxes:
        if t['amount'] == 15.0:
            rpc('account.tax', 'write', [[t['id']], {'amount': 13.0, 'name': t['name'].replace('15', '13')}])
    print('已将 15% 税率修正为 13%')
else:
    print('已存在 13% 税率，无需修正')

# ===== 5. 再订货规则 =====
print('===== 5. 再订货规则 =====')
# 材料类产品（采购件）加最小库存规则
mats = rpc('product.template', 'search_read', [[['purchase_ok', '=', True], ['sale_ok', '=', False],
                                                ['type', '=', 'consu']]],
           {'fields': ['name'], 'limit': 30})
print('采购材料: %d 个' % len(mats))
ops = 0
for p in mats:
    ex_rules = rpc('stock.warehouse.orderpoint', 'search_count', [[['product_tmpl_id', '=', p['id']]]])
    if ex_rules:
        continue
    # 找该模板的变体
    pvs = rpc('product.product', 'search_read', [[['product_tmpl_id', '=', p['id']]]], {'fields': ['id']})
    if not pvs:
        continue
    try:
        rpc('stock.warehouse.orderpoint', 'create', [{
            'product_id': pvs[0]['id'],
            'product_min_qty': 100,
            'product_max_qty': 500,
            'location_id': 8,  # WH/Stock 默认
        }])
        ops += 1
    except Exception as e:
        pass
print('新建再订货规则: %d 条' % ops)

print('\n=== 数据补全完成 ===')
