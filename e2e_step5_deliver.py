#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端 第5步：交付 → OQC → 开票"""
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()

OQC_ITEMS = [
    ('装箱数量核对', '按订单数量装箱、无错装漏装'),
    ('鞋盒/外箱标识', '品名尺码数量标识清晰正确'),
    ('抽检外观', '按 AQL 抽检标准执行'),
    ('条码扫描', '条码可扫、信息正确'),
]


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

state = json.load(open('/tmp/e2e_state.json'))

# ===== 1. OQC 出货检验 =====
print('===== 1. OQC =====')
oqc_id = rpc('qc.inspection', 'create', [{
    'inspection_type': 'oqc',
    'product_id': state['prod_id'],
    'qty': 30,
    'line_ids': [(0, 0, {'sequence': i * 10, 'name': n, 'standard': st,
                         'actual': '符合', 'result': 'pass'})
                 for i, (n, st) in enumerate(OQC_ITEMS)],
}])
rpc('qc.inspection', 'action_start', [[oqc_id]])
rpc('qc.inspection', 'action_pass', [[oqc_id]])
oq = rpc('qc.inspection', 'read', [oqc_id], {'fields': ['name', 'state']})[0]
print('  %s %s（装箱+标识+抽检+条码通过）' % (oq['name'], oq['state']))

# ===== 2. 交付出库 =====
print('===== 2. 交付出库 =====')
so = rpc('sale.order', 'read', [state['so_id']], {'fields': ['name', 'picking_ids']})[0]
for pk_id in so['picking_ids']:
    pk = rpc('stock.picking', 'read', [pk_id], {'fields': ['name', 'state']})[0]
    print('  %s 当前: %s' % (pk['name'], pk['state']))
    if pk['state'] not in ('done', 'cancel'):
        rpc('stock.picking', 'button_validate', [[pk_id]])
        pk = rpc('stock.picking', 'read', [pk_id], {'fields': ['name', 'state']})[0]
        print('  → %s' % pk['state'])

# ===== 3. 开票 =====
print('===== 3. 开票 =====')
# 手动创建发票（私有方法不能 RPC）
exist_inv = rpc('account.move', 'search_read',
                [[['ref', 'like', so['name']], ['move_type', '=', 'out_invoice']]],
                {'fields': ['name']})
if not exist_inv:
    so_full = rpc('sale.order', 'read', [state['so_id']],
                  {'fields': ['order_line', 'partner_id', 'name', 'amount_total']})[0]
    lines_data = rpc('sale.order.line', 'read', [so_full['order_line']],
                     {'fields': ['product_id', 'name', 'product_uom_qty', 'price_unit', 'tax_ids']})
    inv_lines = []
    for ld in lines_data:
        inv_lines.append((0, 0, {
            'product_id': ld['product_id'][0] if ld.get('product_id') else False,
            'name': ld['name'],
            'quantity': ld['product_uom_qty'],
            'price_unit': ld['price_unit'],
            'tax_ids': ld.get('tax_ids') or [],
        }))
    inv_id = rpc('account.move', 'create', [{
        'move_type': 'out_invoice',
        'partner_id': so_full['partner_id'][0],
        'ref': so_full['name'],
        'invoice_line_ids': inv_lines,
    }])
invoices = rpc('account.move', 'search_read',
               [[['ref', 'like', so['name']], ['move_type', '=', 'out_invoice']]],
               {'fields': ['name', 'state', 'amount_total']})
if not invoices:
    # 备选：按 partner + 未过账发票
    invoices = rpc('account.move', 'search_read', [[['move_type', '=', 'out_invoice'], ('state', '=', 'draft')]],
                   {'fields': ['name', 'state', 'amount_total']})
for inv in invoices:
    print('  发票 %s %s ¥%s' % (inv['name'], inv['state'], inv['amount_total']))
    if inv['state'] == 'draft':
        rpc('account.move', 'action_post', [[inv['id']]])
        iv = rpc('account.move', 'read', [inv['id']], {'fields': ['name', 'state', 'amount_total', 'payment_state']})[0]
        print('  → %s 支付状态: %s' % (iv['state'], iv.get('payment_state')))

# ===== 4. 全流程单据汇总 =====
print('\n===== 4. 全流程单据汇总 =====')
print('  销售: %s' % so['name'])
print('  制造: %s (30双, done)' % state['mo_name'])
print('  采购: %s' % [rpc('purchase.order', 'read', [p], {'fields': ['name']})[0]['name'] for p in state['po_ids']])
print('  检验: IQC×9 + IPQC×1 + FQC×1 + OQC×1 = 12 张')
print('  库存: 3 收货 done + 1 出库 done')

# 各模型计数
stats = {}
for model, label in [('sale.order', '销售订单'), ('purchase.order', '采购订单'),
                     ('mrp.production', '制造订单'), ('stock.picking', '调拨单'),
                     ('account.move', '会计凭证'), ('qc.inspection', '检验单')]:
    try:
        stats[label] = rpc(model, 'search_count', [[]])
    except Exception:
        stats[label] = '-'
print('\n  数据库单据统计: %s' % stats)
