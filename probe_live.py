#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 探测线上系统（220.162.99.166:88）的数据情况
import json
import urllib.request

URL = 'http://220.162.99.166:88'


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


DB = PWD = None
for db in ('odk_erp', 'odoo20', 'odoo'):
    try:
        uid = call('common', 'authenticate', db, 'admin', 'admin', {})
        if uid:
            DB, PWD = db, 'admin'
            print('[OK] 线上认证成功 db=%s uid=%s' % (db, uid))
            break
    except Exception as e:
        print('db=%s 认证失败: %s' % (db, str(e)[:150]))
if not DB:
    raise SystemExit('线上认证失败')


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def count(model, domain):
    return ex(model, 'search_count', domain)


# 1) 已安装的关键模块
print()
print('== 已安装模块 ==')
want = ['mrp', 'purchase_stock', 'stock', 'mrp_account', 'odk_tech',
        'odk_subcontract', 'odk_quality', 'odk_scan', 'odk_http_shim']
mods = ex('ir.module.module', 'search_read',
          [('name', 'in', want)], ['name', 'state'], **{'limit': 50})
for m in sorted(mods, key=lambda x: x['name']):
    print('  %-16s %s' % (m['name'], m['state']))

# 2) 基础数据情况
print()
print('== 线上数据情况 ==')
print('  产品模板总数   :', count('product.template', []))
print('  A-001 是否存在 :', bool(ex('product.template', 'search',
                                    [('default_code', '=', 'A-001')], limit=1)))
print('  BOM 总数       :', count('mrp.bom', []))
print('  生产订单总数   :', count('mrp.production', []))
print('  采购单总数     :', count('purchase.order', []))
print('  供应商数       :', count('res.partner', [('supplier_rank', '>', 0)]))
print('  仓库数         :', count('stock.warehouse', []))

# 3) 最近 5 张生产订单
mos = ex('mrp.production', 'search_read', [], ['name', 'state', 'product_id', 'product_qty'],
         **{'order': 'id desc', 'limit': 5})
print()
print('== 最近生产订单 ==')
for m in mos:
    print('  %-14s %-10s %s × %s' % (m['name'], m['state'],
                                     m['product_id'][1] if m['product_id'] else '-',
                                     m['product_qty']))

# 4) 最近 5 张采购单
pos = ex('purchase.order', 'search_read', [], ['name', 'state', 'partner_id'],
         **{'order': 'id desc', 'limit': 5})
print()
print('== 最近采购单 ==')
for p in pos:
    print('  %-10s %-10s %s' % (p['name'], p['state'],
                                p['partner_id'][1] if p['partner_id'] else '-'))
