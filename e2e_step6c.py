#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾 v2：wizard 收款 + T002 云驰的 PLM 变更 + 全景统计"""
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

# ===== 1. 收款（register wizard 标准流程） =====
print('===== 1. 收款 =====')
inv = rpc('account.move', 'search_read', [[['move_type', '=', 'out_invoice'], ['state', '=', 'posted']]],
          {'fields': ['name', 'amount_total', 'payment_state']})[0]
print('  发票: %s ¥%s %s' % (inv['name'], inv['amount_total'], inv['payment_state']))
bank = rpc('account.journal', 'search_read', [[['type', '=', 'bank']]], {'fields': ['id']})[0]
wiz_id = rpc('account.payment.register', 'create', [{
    'journal_id': bank['id'],
}], {'context': {'active_model': 'account.move', 'active_ids': [inv['id']]}})
rpc('account.payment.register', 'action_create_payments', [[wiz_id]],
    {'context': {'active_model': 'account.move', 'active_ids': [inv['id']]}})
inv2 = rpc('account.move', 'read', [inv['id']], {'fields': ['payment_state', 'amount_residual']})[0]
print('  → %s 余额 ¥%s' % (inv2['payment_state'], inv2['amount_residual']))

# ===== 2. PLM 变更（用无订单占用的 T002 云驰） =====
print('===== 2. PLM 工程变更 =====')
tmpl = rpc('product.template', 'search_read', [[['default_code', '=', 'ADK-T002']]],
           {'fields': ['id', 'name']})[0]
bom = rpc('mrp.bom', 'search_read', [[['product_tmpl_id', '=', tmpl['id']], ['active', '=', True]]],
          {'fields': ['id', 'code']})[0]
print('  产品: %s | BOM: %s' % (tmpl['name'], bom['code']))

eco_id = rpc('plm.eco', 'create', [{
    'subject': '云驰鞋面升级：普通网布→高透气飞织',
    'eco_type': 'material',
    'product_tmpl_id': tmpl['id'],
    'bom_id': bom['id'],
    'reason': '竞品普遍升级飞织鞋面，为保持越野跑鞋品类竞争力并改善透气性，实施材料替代。',
    'description': '材料替代：鞋面网布 → 高透气飞织面料，克重不变，成本+8%，售价可上调。',
}])
rpc('plm.eco', 'action_submit', [[eco_id]])
rpc('plm.eco', 'action_approve', [[eco_id]])
rpc('plm.eco', 'action_apply', [[eco_id]])
eco = rpc('plm.eco', 'read', [eco_id],
          {'fields': ['name', 'state', 'new_bom_id', 'applied_date']})[0]
print('  ECO %s: 草稿→评审→批准→执行 = %s' % (eco['name'], eco['state']))
print('  新版本BOM: %s | 执行: %s' % (eco['new_bom_id'], eco['applied_date']))
old = rpc('mrp.bom', 'read', [bom['id']], {'fields': ['code', 'active']})[0]
print('  旧版 %s 归档=%s' % (old['code'], old['active']))

# ===== 3. 最终全景 =====
print('\n===== 3. 最终全景 =====')
for model, label in [('sale.order', '销售订单'), ('purchase.order', '采购订单'),
                     ('mrp.production', '制造订单'), ('stock.picking', '调拨单'),
                     ('account.move', '会计凭证'), ('qc.inspection', '质量检验单'),
                     ('plm.eco', '工程变更单'), ('mrp.bom', 'BOM'),
                     ('mrp.bom.line', 'BOM材料行'), ('mrp.routing.workcenter', '工序'),
                     ('stock.warehouse.orderpoint', '再订货规则'),
                     ('res.partner', '业务伙伴'), ('product.template', '产品')]:
    try:
        print('  %-12s %s' % (label, rpc(model, 'search_count', [[]])))
    except Exception:
        pass

# 检验单分型统计
for t, ln in [('iqc', 'IQC'), ('ipqc', 'IPQC'), ('fqc', 'FQC'), ('oqc', 'OQC')]:
    try:
        print('  %-12s %s' % (ln, rpc('qc.inspection', 'search_count', [[['inspection_type', '=', t]]])))
    except Exception:
        pass
