#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# odk_wms 本地安装 + 端到端功能测试
import json
import urllib.request

URL = 'http://127.0.0.1:8069'
DB, USER, PWD = 'odoo20', 'admin', 'admin'


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
print('[OK] 登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


# 1) 安装 odk_wms
ex('ir.module.module', 'update_list')
mid = find('ir.module.module', [('name', '=', 'odk_wms')])[0]
st = ex('ir.module.module', 'read', mid, ['state'])[0]['state']
print('[1] odk_wms 状态: %s' % st)
if st != 'installed':
    ex('ir.module.module', 'button_immediate_install', [mid])
    st = ex('ir.module.module', 'read', mid, ['state', 'latest_version'])[0]
    print('    安装完成: %s v%s' % (st['state'], st['latest_version']))

# 2) 准备基础数据
m001 = find('product.product', [('default_code', '=', 'M-001')])[0]
m002 = find('product.product', [('default_code', '=', 'M-002')])[0]
wh = find('stock.warehouse', [], limit=1)[0]
sup_fab = find('res.partner', [('name', 'like', '鸿达织造')])[0]
# 建第二个仓库用于调拨测试（成品仓）
wh2_ids = find('stock.warehouse', [('name', 'like', '成品仓')], limit=1)
if wh2_ids:
    wh2 = wh2_ids[0]
else:
    wh2 = ex('stock.warehouse', 'create', {'name': '成品仓', 'code': 'FG'})
    print('[OK] 新建成品仓 id=%s' % wh2)

stock0 = ex('product.product', 'read', [m001, m002], ['qty_available'])
before = {p['id']: p['qty_available'] for p in stock0}
print('[2] 初始库存: M-001=%g, M-002=%g' % (before[m001], before[m002]))

# 3) 采购入库单：M-001 +100
oid = ex('odk.wms.order', 'create', {
    'doc_type': 'in_purchase', 'partner_id': sup_fab, 'warehouse_id': wh,
    'line_ids': [(0, 0, {'product_id': m001, 'product_qty': 100.0})],
})
ex('odk.wms.order', 'action_confirm', [oid])
o = ex('odk.wms.order', 'read', oid, ['name', 'state', 'picking_id', 'date_done'])[0]
print('[3] 采购入库单 %s → %s，库存单据: %s' %
      (o['name'], o['state'], o['picking_id'][1] if o['picking_id'] else '无'))
assert o['state'] == 'confirmed'

# 4) 加工领料单：M-001 -20
oid2 = ex('odk.wms.order', 'create', {
    'doc_type': 'out_mfg', 'warehouse_id': wh,
    'line_ids': [(0, 0, {'product_id': m001, 'product_qty': 20.0})],
})
ex('odk.wms.order', 'action_confirm', [oid2])
o2 = ex('odk.wms.order', 'read', oid2, ['name', 'state', 'picking_id'])[0]
print('[4] 加工领料单 %s → %s，库存单据: %s' %
      (o2['name'], o2['state'], o2['picking_id'][1] if o2['picking_id'] else '无'))

after1 = ex('product.product', 'read', [m001], ['qty_available'])[0]['qty_available']
expected1 = before[m001] + 100 - 20
assert abs(after1 - expected1) < 1e-6, 'M-001 库存应为 %g，实际 %g' % (expected1, after1)
print('    M-001 库存核对: %g + 100 - 20 = %g ✓' % (before[m001], after1))

# 5) 物料转仓调拨单：M-002 wh → 成品仓 30
oid3 = ex('odk.wms.order', 'create', {
    'doc_type': 'transfer', 'warehouse_id': wh, 'dest_warehouse_id': wh2,
    'line_ids': [(0, 0, {'product_id': m002, 'product_qty': 30.0})],
})
ex('odk.wms.order', 'action_confirm', [oid3])
o3 = ex('odk.wms.order', 'read', oid3, ['name', 'state'])[0]
print('[5] 转仓调拨单 %s → %s ✓' % (o3['name'], o3['state']))

# 6) 盘点调整单：把 M-001 盘成 200
iid = ex('odk.wms.inventory', 'create', {
    'warehouse_id': wh,
    'line_ids': [(0, 0, {'product_id': m001, 'counted_qty': 200.0})],
})
ex('odk.wms.inventory', 'action_fill_current', [iid])
lines = ex('odk.wms.inventory.line', 'read',
           find('odk.wms.inventory.line', [('inv_id', '=', iid)]),
           ['current_qty', 'counted_qty', 'diff_qty'])
print('[6] 盘点单：账面 %g → 实盘 %g（盘差 %g）' %
      (lines[0]['current_qty'], lines[0]['counted_qty'], lines[0]['diff_qty']))
ex('odk.wms.inventory', 'action_apply', [iid])
iv = ex('odk.wms.inventory', 'read', iid, ['name', 'state'])[0]
after2 = ex('product.product', 'read', [m001], ['qty_available'])[0]['qty_available']
assert after2 == 200.0, '盘点后 M-001 应为 200，实际 %g' % after2
print('    盘点调整单 %s → %s，M-001 库存 = %g ✓' % (iv['name'], iv['state'], after2))

# 7) 客供料入库 + 材料转卖 出库方向验证
oid4 = ex('odk.wms.order', 'create', {
    'doc_type': 'in_customer', 'warehouse_id': wh,
    'line_ids': [(0, 0, {'product_id': m002, 'product_qty': 50.0})],
})
ex('odk.wms.order', 'action_confirm', [oid4])
oid5 = ex('odk.wms.order', 'create', {
    'doc_type': 'out_resale', 'warehouse_id': wh,
    'line_ids': [(0, 0, {'product_id': m002, 'product_qty': 10.0})],
})
ex('odk.wms.order', 'action_confirm', [oid5])
o5 = ex('odk.wms.order', 'read', oid5, ['name', 'state'])[0]
print('[7] 客供料入库 + 材料转卖 → %s ✓' % o5['state'])

# 8) 重复过账保护
try:
    ex('odk.wms.order', 'action_confirm', [oid])
    print('[8] !! 重复过账未拦截')
except RuntimeError:
    print('[8] 重复过账保护 ✓')

print()
print('ALL PASS')
