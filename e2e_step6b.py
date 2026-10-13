#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾修复：发票收款核销 + PLM变更单 + 最终统计"""
import json

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

# ===== 1. 收款核销 =====
print('===== 1. 收款核销 =====')

inv = rpc('account.move', 'search_read', [[['move_type', '=', 'out_invoice'], ['state', '=', 'posted']]],
          {'fields': ['name', 'amount_total', 'payment_state', 'line_ids']})[0]
print('  发票: %s ¥%s %s' % (inv['name'], inv['amount_total'], inv['payment_state']))
# 找应收行并核销
lines = rpc('account.move.line', 'search_read',
            [[['move_id', '=', inv['id']], ['account_type', '=', 'asset_receivable'],
              ['balance', '!=', 0]]], {'fields': ['id', 'balance']})
print('  应收行: %s' % [(l['id'], l['balance']) for l in lines])
for ln in lines:
    rpc('account.move', 'js_assign_outstanding_line', [[inv['id']], ln['id']])
inv2 = rpc('account.move', 'read', [inv['id']], {'fields': ['name', 'payment_state', 'amount_residual']})[0]
print('  核销后: %s → %s (余额 ¥%s)' % (inv2['name'], inv2['payment_state'], inv2['amount_residual']))

# ===== 2. PLM 工程变更 =====
print('===== 2. PLM 工程变更 =====')
state = json.load(open('/tmp/e2e_state.json'))
tmpl = rpc('product.product', 'read', [state['prod_id']],
           {'fields': ['product_tmpl_id']})[0]['product_tmpl_id'][0]
bom = rpc('mrp.bom', 'search_read', [[['product_tmpl_id', '=', tmpl], ['active', '=', True]]],
          {'fields': ['id', 'code']})
bom = [b for b in bom if 'ADK-H001' in (b.get('code') or '')][0]
print('  当前BOM: %s' % bom['code'])

eco_id = rpc('plm.eco', 'create', [{
    'subject': '征途Pro鞋垫升级：普通乳胶→高回弹记忆棉',
    'eco_type': 'material',
    'product_tmpl_id': tmpl,
    'bom_id': bom['id'],
    'reason': '客户反馈长时间徒步足部疲劳，升级高回弹记忆棉鞋垫提升舒适度与品牌溢价。',
    'description': '材料替代：ML-INS-001 乳胶鞋垫 → 记忆棉鞋垫（新增 SKU），其余工艺不变。',
}])
eco = rpc('plm.eco', 'read', [eco_id], {'fields': ['name', 'state']})[0]
print('  ECO %s: %s' % (eco['name'], eco['state']))
rpc('plm.eco', 'action_submit', [[eco_id]])
rpc('plm.eco', 'action_approve', [[eco_id]])
rpc('plm.eco', 'action_apply', [[eco_id]])
eco = rpc('plm.eco', 'read', [eco_id],
          {'fields': ['name', 'state', 'new_bom_id', 'applied_date']})[0]
print('  流转: 草稿→评审→批准→执行 = %s' % eco['state'])
print('  新版本BOM: %s | 执行日期: %s' % (eco['new_bom_id'], eco['applied_date']))
old = rpc('mrp.bom', 'read', [bom['id']], {'fields': ['code', 'active']})[0]
print('  旧版 %s 归档=%s' % (old['code'], old['active']))

# ===== 3. 最终统计 =====
print('\n===== 3. 最终全景 =====')
for model, label in [('sale.order', '销售订单'), ('purchase.order', '采购订单'),
                     ('mrp.production', '制造订单'), ('stock.picking', '调拨单'),
                     ('account.move', '会计凭证'), ('account.payment', '付款单'),
                     ('qc.inspection', '质量检验单'), ('plm.eco', '工程变更单'),
                     ('mrp.bom', 'BOM'), ('mrp.bom.line', 'BOM材料行'),
                     ('mrp.routing.workcenter', '工序'), ('stock.warehouse.orderpoint', '再订货规则')]:
    try:
        cnt = rpc(model, 'search_count', [[]])
        print('  %-12s %s' % (label, cnt))
    except Exception:
        pass
