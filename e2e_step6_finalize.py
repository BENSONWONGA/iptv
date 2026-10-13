#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收尾：清理重复OQC → 收款 → PLM变更单全流程演示"""
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

# ===== 1. 清理重复 OQC =====
print('===== 1. 清理重复 OQC =====')
oqcs = rpc('qc.inspection', 'search_read', [[['inspection_type', '=', 'oqc']]],
           {'fields': ['name', 'state'], 'order': 'id asc'})
print('  现有 OQC: %s' % [(o['name'], o['state']) for o in oqcs])
if len(oqcs) > 1:
    # 保留最后一张，取消其余
    for o in oqcs[:-1]:
        rpc('qc.inspection', 'action_cancel', [[o['id']]])
        print('  取消重复: %s' % o['name'])
oqcs2 = rpc('qc.inspection', 'search_read', [[['inspection_type', '=', 'oqc']]],
            {'fields': ['name', 'state']})
print('  最终: %s' % [(o['name'], o['state']) for o in oqcs2])

# ===== 2. 收款 =====
print('===== 2. 收款 =====')
inv = rpc('account.move', 'search_read', [[['move_type', '=', 'out_invoice'], ['state', '=', 'posted']]],
          {'fields': ['name', 'amount_total', 'partner_id', 'payment_state']})[0]
print('  发票: %s ¥%s 状态:%s' % (inv['name'], inv['amount_total'], inv['payment_state']))
bank = rpc('account.journal', 'search_read', [[['type', '=', 'bank']]], {'fields': ['id']})[0]
pay_id = rpc('account.payment', 'create', [{
    'payment_type': 'inbound',
    'partner_type': 'customer',
    'partner_id': inv['partner_id'][0],
    'amount': inv['amount_total'],
    'journal_id': bank['id'],
}])
rpc('account.payment', 'action_post', [[pay_id]])
inv2 = rpc('account.move', 'read', [inv['id']], {'fields': ['name', 'payment_state']})[0]
print('  收款后: %s → %s' % (inv2['name'], inv2['payment_state']))

# ===== 3. PLM 工程变更单全流程 =====
print('===== 3. PLM 工程变更 =====')
state = json.load(open('/tmp/e2e_state.json'))
tmpl = rpc('product.product', 'read', [state['prod_id']],
           {'fields': ['product_tmpl_id']})[0]['product_tmpl_id']
bom = rpc('mrp.bom', 'search_read', [[['product_tmpl_id', '=', tmpl]]], {'fields': ['id', 'code', 'active']})[0]
print('  当前 BOM: %s (active=%s)' % (bom['code'], bom['active']))

eco_id = rpc('plm.eco', 'create', [{
    'subject': '征途Pro鞋垫升级：普通乳胶→高回弹记忆棉',
    'eco_type': 'material',
    'product_tmpl_id': tmpl,
    'bom_id': bom['id'],
    'reason': '客户反馈长时间徒步足部疲劳，升级高回弹记忆棉鞋垫提升舒适度与品牌溢价。',
    'description': '材料替代：ML-INS-001 乳胶鞋垫 → 记忆棉鞋垫（新增 SKU），其余工艺不变。',
}])
eco = rpc('plm.eco', 'read', [eco_id], {'fields': ['name', 'state']})[0]
print('  ECO %s 创建: %s' % (eco['name'], eco['state']))

rpc('plm.eco', 'action_submit', [[eco_id]])
rpc('plm.eco', 'action_approve', [[eco_id]])
rpc('plm.eco', 'action_apply', [[eco_id]])
eco = rpc('plm.eco', 'read', [eco_id],
          {'fields': ['name', 'state', 'new_bom_id', 'approved_by', 'applied_date']})[0]
print('  流转: 草稿→评审→批准→执行 = %s' % eco['state'])
print('  新版本BOM: %s | 执行日期: %s' % (eco['new_bom_id'], eco['applied_date']))
old = rpc('mrp.bom', 'read', [bom['id']], {'fields': ['code', 'active']})[0]
print('  旧版BOM %s 已归档 (active=%s)' % (old['code'], old['active']))

# ===== 4. 最终全景统计 =====
print('\n===== 4. 最终全景 =====')
for model, label in [('sale.order', '销售订单'), ('purchase.order', '采购订单'),
                     ('mrp.production', '制造订单'), ('stock.picking', '调拨单'),
                     ('account.move', '会计凭证'), ('account.payment', '付款单'),
                     ('qc.inspection', '质量检验单'), ('plm.eco', '工程变更单'),
                     ('mrp.bom', 'BOM'), ('mrp.bom.line', 'BOM材料行'),
                     ('mrp.routing.workcenter', '工序'),
                     ('stock.warehouse.orderpoint', '再订货规则')]:
    try:
        cnt = rpc(model, 'search_count', [[]])
        print('  %-10s %s' % (label, cnt))
    except Exception:
        pass
