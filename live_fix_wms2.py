#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 补完盘点自检（新版实现）+ 收尾
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


pid = find('product.product', [('default_code', '=', 'WMS-TEST')])[0]

# 1) 找到草稿盘点单 PD-0001（上次自检中断遗留），重新带出账面并执行
inv_ids = ex('odk.wms.inventory', 'search',
             [('state', '=', 'draft')], limit=5)
inv = inv_ids[0]
name = ex('odk.wms.inventory', 'read', inv, ['name'])[0]['name']
print('[1] 执行盘点单 %s' % name)
ex('odk.wms.inventory', 'action_fill_current', [inv])
line = ex('odk.wms.inventory.line', 'read',
          find('odk.wms.inventory.line', [('inv_id', '=', inv)]),
          ['current_qty', 'counted_qty', 'diff_qty'])[0]
print('    账面=%g 实盘=%g 盘差=%g' %
      (line['current_qty'], line['counted_qty'], line['diff_qty']))
assert line['current_qty'] == 50, '材料仓账面应为 50，实际 %g' % line['current_qty']

ex('odk.wms.inventory', 'action_apply', [inv])
r = ex('odk.wms.inventory', 'read', inv, ['name', 'state', 'date_done'])[0]
q = ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']
print('[2] 盘点 %s → %s | WMS-TEST 总库存=%g（期望75）' % (r['name'], r['state'], q))
assert r['state'] == 'done' and q == 75

# 3) 核对生成的盘亏库存移动
moves = ex('stock.move', 'search_read', [('origin', '=', name)],
           ['name', 'product_uom_qty', 'quantity', 'state', 'location_id',
            'location_dest_id'], limit=5)
for m in moves:
    print('    盘亏移动: %s 数量=%g 状态=%s' % (m['name'][:40], m['quantity'], m['state']))
assert moves and all(m['state'] == 'done' for m in moves)

# 4) 收尾：测试物料归档
ex('product.product', 'write', [pid], {'active': False})
print('[3] 测试物料已归档（单据/移动轨迹保留）')

print()
print('SELF-TEST COMPLETE')
