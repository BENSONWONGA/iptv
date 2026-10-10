#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# odk_dispatch 线上端到端自检：派工 → 领料 → 部件入库 → 日报 → 自动完工
import json
import urllib.request

URL = 'http://220.162.99.166:88'
DB, USER, PWD = 'odk_erp', 'admin', 'admin'


def call(service, method, *args):
    payload = {'jsonrpc': '2.0', 'method': 'call',
               'params': {'service': service, 'method': method, 'args': list(args)}}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL + '/jsonrpc', data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=600) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(str(out['error'])[:900])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})
print('[OK] 线上登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


def q(pid):
    return ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']


# 0) 测试物料
pids = find('product.product', [('default_code', '=', 'WMS-TEST2')])
if pids:
    pid = pids[0]
    ex('product.product', 'write', [pid], {'active': True})
else:
    pid = ex('product.product', 'create', {
        'name': '派工测试部件', 'default_code': 'WMS-TEST2', 'is_storable': True,
    })
print('[0] 测试部件 WMS-TEST2 id=%s，当前库存=%g' % (pid, q(pid)))

wh = find('stock.warehouse', [], limit=1)[0]

# 1) 先采购入库 +10，保证有料可领
o1 = ex('odk.wms.order', 'create', {
    'doc_type': 'in_purchase', 'warehouse_id': wh, 'note': '派工模块自检备料',
    'line_ids': [(0, 0, {'product_id': pid, 'product_qty': 10.0})],
})
ex('odk.wms.order', 'action_confirm', [o1])
print('[1] 备料入库 +10 → 库存=%g' % q(pid))
assert q(pid) == 10

# 2) 冲裁派工单：派工 → 开工
d = ex('odk.dispatch', 'create', {
    'dispatch_type': 'cutting', 'product_id': pid, 'qty': 10.0,
    'operation': '冲裁', 'user_id': uid, 'note': '系统上线自检',
})
ex('odk.dispatch', 'action_assign', [d])
ex('odk.dispatch', 'action_start', [d])
r = ex('odk.dispatch', 'read', d, ['name', 'state'])[0]
print('[2] 冲裁派工单 %s → %s' % (r['name'], r['state']))
assert r['state'] == 'producing'

# 3) 派工领料单（挂派工单）：-10
o2 = ex('odk.wms.order', 'create', {
    'doc_type': 'out_mfg', 'warehouse_id': wh, 'dispatch_id': d,
    'picker_id': uid, 'note': '派工领料自检',
    'line_ids': [(0, 0, {'product_id': pid, 'product_qty': 10.0})],
})
ex('odk.wms.order', 'action_confirm', [o2])
print('[3] 派工领料 -10 → 库存=%g' % q(pid))
assert q(pid) == 0
o2r = ex('odk.wms.order', 'read', o2, ['name', 'dispatch_id', 'picker_id'])[0]
print('    %s 已挂派工单 %s，领料人=%s' %
      (o2r['name'], o2r['dispatch_id'][1], o2r['picker_id'][1]))
assert o2r['dispatch_id'][0] == d

# 4) 指令部件入库单（挂派工单）：+10 完工部件回库
o3 = ex('odk.wms.order', 'create', {
    'doc_type': 'in_part', 'warehouse_id': wh, 'dispatch_id': d,
    'note': '冲裁完工部件入库',
    'line_ids': [(0, 0, {'product_id': pid, 'product_qty': 10.0})],
})
ex('odk.wms.order', 'action_confirm', [o3])
print('[4] 指令部件入库 +10 → 库存=%g' % q(pid))
assert q(pid) == 10

# 5) 派工日报：确认 → 计件金额 + 完工数累加 → 报满自动完工
rep = ex('odk.dispatch.report', 'create', {
    'dispatch_id': d, 'qty_produced': 10.0, 'qty_scrapped': 0.0,
    'work_hours': 8.0, 'rate': 2.5, 'note': '自检日报',
})
ex('odk.dispatch.report', 'action_confirm', [rep])
rr = ex('odk.dispatch.report', 'read', rep,
        ['name', 'state', 'amount', 'qty_produced'])[0]
print('[5] 日报 %s → %s，合格10 × 单价2.5 = 计件金额 %g' %
      (rr['name'], rr['state'], rr['amount']))
assert rr['state'] == 'confirmed' and abs(rr['amount'] - 25.0) < 1e-6

dr = ex('odk.dispatch', 'read', d, ['name', 'state', 'qty_done', 'date_actual'])[0]
print('[6] 派工单 %s → %s，完工数量=%g（报满自动完工）' %
      (dr['name'], dr['state'], dr['qty_done']))
assert dr['state'] == 'done' and dr['qty_done'] == 10

# 7) 收尾：测试物料归档
ex('product.product', 'write', [pid], {'active': False})
print('[7] 测试部件已归档（单据/日报/派工单轨迹保留）')

print()
print('DISPATCH SELF-TEST ALL PASS')
