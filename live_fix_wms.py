#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 线上修复：重复内部调拨类型单号前缀 + 补完 odk_wms 自检
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


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


# 1) 看看 picking type 有哪些跟单号相关的字段
fields = ex('stock.picking.type', 'fields_get', [], ['string', 'type'])
seq_fields = {k: v['string'] for k, v in fields.items()
              if 'sequence' in k or k in ('code', 'name')}
print('[1] 单号相关字段:', list(seq_fields.keys()))

# 2) 已存在的 WH/INT/00001 属于哪个类型
p = ex('stock.picking', 'search_read', [('name', '=', 'WH/INT/00001')],
       ['picking_type_id'], limit=1)[0]
owner = p['picking_type_id'][0]
print('[2] WH/INT/00001 属于类型 id=%s' % owner)

# 3) WH 的两个内部调拨类型
internals = ex('stock.picking.type', 'search_read',
               [('code', '=', 'internal'), ('warehouse_id', '=', 1)],
               ['name', 'sequence_id'])
print('[3] WH 内部调拨类型: %s' % [(t['id'], t['name']) for t in internals])
other = [t for t in internals if t['id'] != owner]
assert len(other) == 1, '预期恰好 1 个重复类型'
other = other[0]
print('    重复类型 id=%s（改名前缀为 WH/TRA/）' % other['id'])

# 4) 修改重复类型的序列前缀
seq_id = other['sequence_id'][0]
ex('ir.sequence', 'write', [seq_id], {'prefix': 'WH/TRA/'})
s = ex('ir.sequence', 'read', [seq_id], ['prefix', 'code', 'number_next'])[0]
print('[4] 序列已改: prefix=%s next=%s' % (s['prefix'], s['number_next']))
# 如有 sequence_code 之类的字段一并看下
for f in ('sequence_code',):
    if f in fields:
        tv = ex('stock.picking.type', 'read', other['id'], [f])[0]
        print('    类型 %s=%s' % (f, tv[f]))

# 5) 补完自检：确认转仓单 WMS-0003
oid = find('odk.wms.order', [('name', '=', 'WMS-0003')])[0]
ex('odk.wms.order', 'action_confirm', [oid])
r = ex('odk.wms.order', 'read', oid, ['name', 'state', 'picking_id'])[0]
pid = find('product.product', [('default_code', '=', 'WMS-TEST')])[0]
q_total = ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']
print('[5] 转仓调拨 %s → %s，库存单据=%s，总库存=%g（期望80）' %
      (r['name'], r['state'], r['picking_id'][1] if r['picking_id'] else '无', q_total))
assert r['state'] == 'confirmed' and q_total == 80

# 6) 盘点调整：材料仓账面 50 → 实盘 45
inv = ex('odk.wms.inventory', 'create', {
    'warehouse_id': 1, 'note': '系统上线自检',
    'line_ids': [(0, 0, {'product_id': pid, 'counted_qty': 45.0})],
})
ex('odk.wms.inventory', 'action_fill_current', [inv])
line = ex('odk.wms.inventory.line', 'read',
          find('odk.wms.inventory.line', [('inv_id', '=', inv)]),
          ['current_qty', 'counted_qty', 'diff_qty'])[0]
print('[6] 盘点: 账面=%g 实盘=%g 盘差=%g' %
      (line['current_qty'], line['counted_qty'], line['diff_qty']))
assert line['current_qty'] == 50 and line['diff_qty'] == -5
ex('odk.wms.inventory', 'action_apply', [inv])
iv = ex('odk.wms.inventory', 'read', inv, ['name', 'state'])[0]
q_total = ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']
print('    盘点单 %s → %s，总库存=%g（期望75）' % (iv['name'], iv['state'], q_total))
assert q_total == 75

# 7) 收尾：测试物料归档
ex('product.product', 'write', [pid], {'active': False})
print('[7] 测试物料已归档（单据轨迹保留）')

print()
print('SELF-TEST COMPLETE — 转仓调拨与盘点均正常')
