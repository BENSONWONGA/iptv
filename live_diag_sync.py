#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 线上自检：1) 全模块同步状态 2) 转仓调拨报错根因诊断
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


print()
print('========= 一、模块同步状态 =========')
mods = ex('ir.module.module', 'search_read',
          [('name', 'like', 'odk%')], ['name', 'state', 'latest_version'])
for m in mods:
    print('  %-16s %-10s v%s' % (m['name'], m['state'], m['latest_version']))

print()
print('========= 二、各业务模块数据就绪情况 =========')
checks = [
    ('odk.mrp.calc', 'MRP运算单'),
    ('odk.mrp.calc.line', 'MRP运算行'),
    ('odk.subcontract.order', '委外加工单'),
    ('odk.subcontract.quote', '工艺报价'),
    ('odk.quality.check', '质检单'),
    ('odk.wms.order', '仓库业务单'),
    ('odk.wms.inventory', '盘点调整单'),
]
for model, label in checks:
    cnt = ex(model, 'search_count', [])
    print('  %-14s %s: %d 条' % (model, label, cnt))

print()
print('========= 三、仓库与库位 =========')
whs = ex('stock.warehouse', 'search_read', [], ['name', 'code'])
for w in whs:
    print('  仓库 id=%s %s (%s)' % (w['id'], w['name'], w['code']))

print()
print('========= 四、转仓调拨报错根因诊断 =========')
print('--- 单据类型（含序列） ---')
ptypes = ex('stock.picking.type', 'search_read', [],
            ['name', 'code', 'warehouse_id', 'sequence_id'],
            limit=30, order='id')
seq_ids = [p['sequence_id'][0] for p in ptypes if p['sequence_id']]
seqs = {s['id']: s for s in ex('ir.sequence', 'read', seq_ids,
                               ['name', 'prefix', 'code', 'number_next'])}
for p in ptypes:
    s = seqs.get(p['sequence_id'][0], {}) if p['sequence_id'] else {}
    print('  id=%-3s %-8s code=%-10s 仓库=%-8s 序列: %s next=%s' % (
        p['id'], p['name'][:12], p['code'],
        p['warehouse_id'][1] if p['warehouse_id'] else '-',
        s.get('prefix', '-'), s.get('number_next', '-')))

print()
print('--- 最近库存单据（找重名） ---')
picks = ex('stock.picking', 'search_read', [],
           ['name', 'state', 'origin'], limit=25, order='id desc')
names = {}
for p in picks:
    print('  %-16s %-10s %s' % (p['name'], p['state'], p.get('origin') or ''))
    names.setdefault(p['name'], 0)
    names[p['name']] += 1
dups = {k: v for k, v in names.items() if v > 1}
print('  重复单号: %s' % (dups or '无'))

print()
print('--- 失败的转仓单状态 ---')
orders = ex('odk.wms.order', 'search_read', [], ['name', 'doc_type', 'state'],
            limit=10, order='id')
for o in orders:
    print('  %-12s %-14s %s' % (o['name'], o['doc_type'], o['state']))

print()
print('DIAG DONE')
