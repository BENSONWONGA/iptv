#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 探测线上 BOM 单耗 / 材料库存 / 供应商报价
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(str(out['error'])[:300])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


# A-001 BOM 明细
shoe_tid = find('product.template', [('default_code', '=', 'A-001')])[0]
bom_id = find('mrp.bom', [('product_tmpl_id', '=', shoe_tid)])[0]
line_ids = ex('mrp.bom.line', 'search', [('bom_id', '=', bom_id)], limit=50)
lines = ex('mrp.bom.line', 'read', line_ids, ['product_id', 'product_qty', 'uom_id'])
print('== 线上 A-001 BOM 每双用量 ==')
mat_ids = []
for l in lines:
    mat_ids.append(l['product_id'][0])
    print('  %-30s x %s %s' % (l['product_id'][1], l['product_qty'],
                              l['uom_id'][1] if l['uom_id'] else ''))

# 材料库存
prods = ex('product.product', 'read', mat_ids,
           ['default_code', 'name', 'qty_available', 'free_qty', 'incoming_qty'])
print()
print('== 线上材料库存 ==')
for p in prods:
    print('  %-7s %-12s 在库 %-8.2f 可用 %-8.2f 在途 %-6.2f' %
          (p['default_code'], p['name'], p['qty_available'], p['free_qty'], p['incoming_qty']))

# 供应商报价档案
sis = ex('product.supplierinfo', 'search_read', [], ['partner_id', 'product_id', 'price'],
         **{'limit': 100})
print()
print('== 线上供应商报价档案 (product.supplierinfo) ==')
for s in sis:
    print('  %-20s %-30s 价格 %s' % (s['partner_id'][1] if s['partner_id'] else '-',
                                     s['product_id'][1] if s['product_id'] else '(模板)',
                                     s['price']))

# 供应商列表
sups = ex('res.partner', 'search_read', [('supplier_rank', '>', 0)], ['name'], limit=20)
print()
print('== 线上供应商 ==')
for s in sups:
    print('  id=%-4s %s' % (s['id'], s['name']))
