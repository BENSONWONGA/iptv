#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端 第4步：生产（IPQC → 完工 → FQC）"""
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()

IPQC_ITEMS = [
    ('首件确认', '首件经确认合格后方可批量生产'),
    ('针距/线迹检查', '针距均匀、无跳线断线、线迹整齐'),
    ('帮面成型质量', '对称平整、无起皱变形'),
    ('胶合强度', '贴合牢固、无开胶溢胶'),
    ('中底/大底贴合', '贴合到位、无偏移'),
]
FQC_ITEMS = [
    ('外观全检', '鞋面整洁、无胶渍划痕、色泽一致'),
    ('左右脚配对', '同双一致、配双正确'),
    ('尺码核对', '鞋内实际尺码与标识一致'),
    ('内部清洁', '鞋腔无杂物、线头清理干净'),
    ('包装及标识', '鞋盒/吊牌/标识正确清晰'),
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
mo_id = state['mo_id']
mo = rpc('mrp.production', 'read', [mo_id],
         {'fields': ['name', 'state', 'components_availability', 'product_qty', 'product_id']})[0]
mo_qty = mo['product_qty']
print('MO: %s | %s | 组件: %s' % (mo['name'], mo['state'], mo['components_availability']))

# ===== 1. 预留材料 =====
print('===== 1. 预留材料 =====')
try:
    rpc('mrp.production', 'action_assign', [[mo_id]])
except Exception as e:
    print('  action_assign: %s' % str(e)[:100])
mo = rpc('mrp.production', 'read', [mo_id],
         {'fields': ['name', 'state', 'components_availability', 'reservation_state']})[0]
print('  → %s | 组件: %s | 预留: %s' % (mo['state'], mo['components_availability'], mo.get('reservation_state')))

# ===== 2. IPQC 制程检验 =====
print('===== 2. IPQC =====')
ipqc_id = rpc('qc.inspection', 'create', [{
    'inspection_type': 'ipqc',
    'product_id': state['prod_id'],
    'qty': mo_qty,
    'production_id': mo_id,
    'line_ids': [(0, 0, {'sequence': i * 10, 'name': n, 'standard': st,
                         'actual': '符合', 'result': 'pass'})
                 for i, (n, st) in enumerate(IPQC_ITEMS)],
}])
rpc('qc.inspection', 'action_start', [[ipqc_id]])
rpc('qc.inspection', 'action_pass', [[ipqc_id]])
ip = rpc('qc.inspection', 'read', [ipqc_id], {'fields': ['name', 'state']})[0]
print('  %s %s（首件+针车+成型检验通过）' % (ip['name'], ip['state']))

# ===== 3. 完工 =====
print('===== 3. 完工 =====')
try:
    rpc('mrp.production', 'button_mark_done', [[mo_id]])
except Exception as e:
    # 可能有 wizard，带 context 重试
    print('  重试: %s' % str(e)[:80])
    rpc('mrp.production', 'button_mark_done', [[mo_id]],
        {'context': {'skip_backorder': True}})
mo = rpc('mrp.production', 'read', [mo_id],
         {'fields': ['name', 'state', 'product_qty', 'qty_producing']})[0]
print('  MO → %s | 生产: %s/%s' % (mo['state'], mo.get('qty_producing'), mo_qty))

# ===== 4. FQC 成品检验 =====
print('===== 4. FQC =====')
fqc_id = rpc('qc.inspection', 'create', [{
    'inspection_type': 'fqc',
    'product_id': state['prod_id'],
    'qty': mo_qty,
    'production_id': mo_id,
    'line_ids': [(0, 0, {'sequence': i * 10, 'name': n, 'standard': st,
                         'actual': '符合', 'result': 'pass'})
                 for i, (n, st) in enumerate(FQC_ITEMS)],
}])
rpc('qc.inspection', 'action_start', [[fqc_id]])
rpc('qc.inspection', 'action_pass', [[fqc_id]])
fq = rpc('qc.inspection', 'read', [fqc_id], {'fields': ['name', 'state']})[0]
print('  %s %s（外观+配对+尺码+清洁+包装全检通过）' % (fq['name'], fq['state']))

# ===== 5. 成品库存验证 =====
time.sleep(2)
prod = rpc('product.product', 'read', [state['prod_id']],
           {'fields': ['qty_available', 'virtual_available']})[0]
print('===== 5. 成品库存 =====')
print('  征途Pro 现货: %s 双' % prod['qty_available'])

state['ipqc_id'] = ipqc_id
state['fqc_id'] = fqc_id
json.dump(state, open('/tmp/e2e_state.json', 'w'))
