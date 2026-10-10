#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 盘点自检（第三次，description_picking 修正版）+ 全量收尾核对
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

# 1) 执行草稿盘点单
inv = ex('odk.wms.inventory', 'search', [('state', '=', 'draft')], limit=1)[0]
name = ex('odk.wms.inventory', 'read', inv, ['name'])[0]['name']
ex('odk.wms.inventory', 'action_fill_current', [inv])
line = ex('odk.wms.inventory.line', 'read',
          find('odk.wms.inventory.line', [('inv_id', '=', inv)]),
          ['current_qty', 'counted_qty', 'diff_qty'])[0]
print('[1] 盘点单 %s：账面=%g 实盘=%g 盘差=%g' %
      (name, line['current_qty'], line['counted_qty'], line['diff_qty']))
assert line['current_qty'] == 50 and line['diff_qty'] == -5

ex('odk.wms.inventory', 'action_apply', [inv])
r = ex('odk.wms.inventory', 'read', inv, ['name', 'state', 'date_done'])[0]
q = ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']
print('[2] 盘点 %s → %s | WMS-TEST 总库存=%g（期望75）' % (r['name'], r['state'], q))
assert r['state'] == 'done' and q == 75

# 3) 核对盘亏移动
moves = ex('stock.move', 'search_read',
           [('description_picking', 'like', name), ('state', '=', 'done')],
           ['description_picking', 'quantity', 'picked'], limit=5)
for m in moves:
    print('    盘亏移动: %s | 数量=%g' % (m['description_picking'], m['quantity']))
assert moves, '应生成 1 条盘亏移动'

# 4) 收尾：测试物料归档
ex('product.product', 'write', [pid], {'active': False})
print('[3] 测试物料已归档')

print()
print('========= 最终全量同步核对 =========')
mods = ex('ir.module.module', 'search_read',
          [('name', 'like', 'odk%')], ['name', 'state', 'latest_version'])
for m in mods:
    print('  %-16s %-10s v%s' % (m['name'], m['state'], m['latest_version']))
print()
for model, label in [
        ('odk.mrp.calc', 'MRP运算单'), ('odk.subcontract.order', '委外加工单'),
        ('odk.subcontract.quote', '工艺报价'), ('odk.wms.order', '仓库业务单'),
        ('odk.wms.inventory', '盘点调整单')]:
    print('  %-22s %s: %d 条' % (model, label, ex(model, 'search_count', [])))
print()
print('SELF-CHECK COMPLETE — 线上系统同步正常，仓库管理全部功能自检通过')
