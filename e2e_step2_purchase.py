#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端 第2步：缺料采购 → 收货"""
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

state = json.load(open('/tmp/e2e_state.json'))
shortage = state['shortage']
print('缺料: %d 种' % len(shortage))

# ===== 1. 供应商分组 =====
sups = rpc('res.partner', 'search_read', [[['supplier_rank', '>', 0]]], {'fields': ['name'], 'limit': 50})
leather = next((p for p in sups if any(k in p['name'] for k in ['皮业', '皮革', '纺织', '布业'])), None)
shoe_mat = next((p for p in sups if any(k in p['name'] for k in ['鞋材', '底业', '橡胶', '材料', '辅料'])), None)
chem = next((p for p in sups if any(k in p['name'] for k in ['化工', '胶水', '贸易'])), None)
# 兜底
others = [p for p in sups if p not in (leather, shoe_mat, chem)]
if not leather:
    leather = others[0] if others else sups[0]
if not shoe_mat:
    shoe_mat = others[1] if len(others) > 1 else sups[1] if len(sups) > 1 else leather
if not chem:
    chem = others[2] if len(others) > 2 else shoe_mat
print('供应商: 皮料→%s 鞋材→%s 化工→%s' % (leather['name'], shoe_mat['name'], chem['name']))


def classify(name):
    if any(k in name for k in ['牛皮', '内里', '缝纫', '鞋带', '鞋楦']):
        return leather
    if any(k in name for k in ['大底', '中底', '鞋垫', '鞋盒']):
        return shoe_mat
    return chem


# ===== 2. 创建采购单 =====
print('===== 2. 创建采购单 =====')
groups = {}
for pid, pname, need, av in shortage:
    sup = classify(pname)
    groups.setdefault(sup['id'], {'sup': sup, 'lines': []})
    groups[sup['id']]['lines'].append((pid, pname, need, av))

po_ids = []
for gid, g in groups.items():
    lines = []
    for pid, pname, need, av in g['lines']:
        qty = (need - av) * 1.1  # 多采 10% 余量
        lines.append((0, 0, {'product_id': pid, 'product_qty': round(qty, 2)}))
    po_id = rpc('purchase.order', 'create', [{
        'partner_id': g['sup']['id'], 'order_line': lines}])
    po = rpc('purchase.order', 'read', [po_id], {'fields': ['name', 'amount_total']})[0]
    print('  PO %s ← %s (%d 种料, ¥%.2f)' % (po['name'], g['sup']['name'], len(lines), po['amount_total']))
    po_ids.append(po_id)

# ===== 3. 确认采购单 =====
print('===== 3. 确认采购 =====')
for po_id in po_ids:
    rpc('purchase.order', 'button_confirm', [[po_id]])
    po = rpc('purchase.order', 'read', [po_id], {'fields': ['name', 'state', 'picking_ids']})[0]
    print('  %s → %s 收货单: %s' % (po['name'], po['state'], po['picking_ids']))

# ===== 4. 收货 =====
print('===== 4. 收货入库 =====')
recv_ids = []
for po_id in po_ids:
    po = rpc('purchase.order', 'read', [po_id], {'fields': ['picking_ids']})[0]
    for pk_id in po['picking_ids']:
        # 填数量并验证
        rpc('stock.picking', 'action_set_quantities_to_inventory', [[pk_id]]) if False else None
        # Odoo 20: 直接 validate（默认数量=需求量）
        try:
            rpc('stock.picking', 'button_validate', [[pk_id]])
        except Exception as e:
            # 可能弹 wizard（如立即回退），尝试 immediate transfer wizard
            print('  重试 %s: %s' % (pk_id, str(e)[:80]))
            rpc('stock.picking', 'button_validate', [[pk_id]])
        pk = rpc('stock.picking', 'read', [pk_id], {'fields': ['name', 'state']})[0]
        print('  %s → %s' % (pk['name'], pk['state']))
        recv_ids.append(pk_id)

state['po_ids'] = po_ids
state['recv_ids'] = recv_ids
state['sups'] = {'leather': leather['id'], 'shoe_mat': shoe_mat['id'], 'chem': chem['id']}
json.dump(state, open('/tmp/e2e_state.json', 'w'))
print('收货完成: %d 张' % len(recv_ids))
