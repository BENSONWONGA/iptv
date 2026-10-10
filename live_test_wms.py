#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# odk_wms 线上端到端自检（专用测试物料，不动真实库存）
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


# 0) 测试物料（专用，结束归档）
pids = find('product.product', [('default_code', '=', 'WMS-TEST')])
if pids:
    pid = pids[0]
    ex('product.product', 'write', [pid], {'active': True})
else:
    pid = ex('product.product', 'create', {
        'name': 'WMS测试物料', 'default_code': 'WMS-TEST', 'is_storable': True,
    })
print('[0] 测试物料 WMS-TEST id=%s' % pid)

wh = find('stock.warehouse', [], limit=1)[0]
wh_ids = find('stock.warehouse', [('name', 'like', '成品仓')])
fg = wh_ids[0] if wh_ids else ex('stock.warehouse', 'create',
                                 {'name': '成品仓', 'code': 'FG'})
print('    材料仓=%s, 成品仓=%s' % (wh, fg))

# 1) 采购入库 +100
o1 = ex('odk.wms.order', 'create', {
    'doc_type': 'in_purchase', 'warehouse_id': wh,
    'note': '系统上线自检',
    'line_ids': [(0, 0, {'product_id': pid, 'product_qty': 100.0})],
})
ex('odk.wms.order', 'action_confirm', [o1])
r1 = ex('odk.wms.order', 'read', o1, ['name', 'state', 'picking_id'])[0]
q = ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']
print('[1] 采购入库 %s → %s | 库存=%g (期望100)' % (r1['name'], r1['state'], q))
assert r1['state'] == 'confirmed' and q == 100

# 2) 加工领料 -20
o2 = ex('odk.wms.order', 'create', {
    'doc_type': 'out_mfg', 'warehouse_id': wh, 'note': '系统上线自检',
    'line_ids': [(0, 0, {'product_id': pid, 'product_qty': 20.0})],
})
ex('odk.wms.order', 'action_confirm', [o2])
q = ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']
print('[2] 加工领料 → 库存=%g (期望80)' % q)
assert q == 80

# 3) 转仓调拨 WH→成品仓 30
o3 = ex('odk.wms.order', 'create', {
    'doc_type': 'transfer', 'warehouse_id': wh, 'dest_warehouse_id': fg,
    'note': '系统上线自检',
    'line_ids': [(0, 0, {'product_id': pid, 'product_qty': 30.0})],
})
ex('odk.wms.order', 'action_confirm', [o3])
r3 = ex('odk.wms.order', 'read', o3, ['name', 'state'])[0]
q = ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']
print('[3] 转仓调拨 %s → %s | 总库存=%g (期望80)' % (r3['name'], r3['state'], q))
assert r3['state'] == 'confirmed' and q == 80

# 4) 盘点调整：WH 账面50 → 实盘45（盘差-5）
inv = ex('odk.wms.inventory', 'create', {
    'warehouse_id': wh, 'note': '系统上线自检',
    'line_ids': [(0, 0, {'product_id': pid, 'counted_qty': 45.0})],
})
ex('odk.wms.inventory', 'action_fill_current', [inv])
lines = ex('odk.wms.inventory.line', 'read',
           find('odk.wms.inventory.line', [('inv_id', '=', inv)]),
           ['current_qty', 'counted_qty', 'diff_qty'])[0]
print('[4] 盘点: 账面=%g 实盘=%g 盘差=%g' %
      (lines['current_qty'], lines['counted_qty'], lines['diff_qty']))
assert lines['current_qty'] == 50 and lines['diff_qty'] == -5
ex('odk.wms.inventory', 'action_apply', [inv])
iv = ex('odk.wms.inventory', 'read', inv, ['name', 'state'])[0]
q = ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']
print('    盘点单 %s → %s | 总库存=%g (期望75)' % (iv['name'], iv['state'], q))
assert q == 75

# 5) 材料库存查询 / IQC 动作数据源就绪
stock_cnt = ex('product.product', 'search_count', [('is_storable', '=', True)])
iqc_cnt = ex('odk.quality.check', 'search_count', [('check_type', '=', 'iqc')])
print('[5] 材料库存查询可查 %d 个产品 | IQC 待检记录 %d 条' % (stock_cnt, iqc_cnt))

# 6) 收尾：测试物料归档（保留单据轨迹，物料不再出现在业务视图）
ex('product.product', 'write', [pid], {'active': False})
print('[6] 测试物料已归档 ✓')

print()
print('LIVE SELF-TEST ALL PASS')
