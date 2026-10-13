#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""端到端 第3步：IQC 来料检验（shoe_qms）"""
import json

import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()

IQC_ITEMS = [
    ('外观检查', '无划伤、色差、污渍、伤残'),
    ('尺寸测量', '与规格书/样品一致，公差范围内'),
    ('材质确认', '材质与确认样品一致'),
    ('数量核对', '实际数量与送货单一致'),
    ('环保/检测报告', '供应商提供有效检测报告'),
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

# ===== 1. 给每张收货单的每个材料建 IQC =====
print('===== 1. 创建 IQC 检验单 =====')
iqc_ids = []
for pk_id in state['recv_ids']:
    moves = rpc('stock.move', 'search_read', [[['picking_id', '=', pk_id]]],
                {'fields': ['product_id', 'quantity', 'partner_id']})
    pk = rpc('stock.picking', 'read', [pk_id], {'fields': ['name', 'partner_id']})[0]
    for mv in moves:
        insp_id = rpc('qc.inspection', 'create', [{
            'inspection_type': 'iqc',
            'product_id': mv['product_id'][0],
            'qty': mv.get('quantity') or 1,
            'partner_id': mv.get('partner_id') and mv['partner_id'][0],
            'picking_id': pk_id,
            'line_ids': [(0, 0, {'sequence': i * 10, 'name': n, 'standard': st,
                                 'actual': '符合', 'result': 'pass'})
                         for i, (n, st) in enumerate(IQC_ITEMS)],
        }])
        iqc_ids.append(insp_id)
        print('  IQC %s ← %s (%s)' % (insp_id, mv['product_id'][1][:20], pk['name']))

# ===== 2. 检验流转：开始 → 合格 =====
print('===== 2. 检验流转 =====')
for iid in iqc_ids:
    rpc('qc.inspection', 'action_start', [[iid]])
    rpc('qc.inspection', 'action_pass', [[iid]])
insps = rpc('qc.inspection', 'search_read', [[['id', 'in', iqc_ids]]],
            {'fields': ['name', 'state', 'product_id']})
for i in insps:
    print('  %s %s %s' % (i['name'], i['state'], i['product_id'][1][:18]))

# 统计
total = rpc('qc.inspection', 'search_count', [[]])
print('IQC 完成: %d 张（库内检验单总数 %d）' % (len(iqc_ids), total))

state['iqc_ids'] = iqc_ids
json.dump(state, open('/tmp/e2e_state.json', 'w'))
