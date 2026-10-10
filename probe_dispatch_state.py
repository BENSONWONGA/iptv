#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 探测线上 odk_dispatch 状态（是否因 report 依赖缺失被跳过）
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
    with urllib.request.urlopen(req, timeout=120) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(str(out['error'])[:600])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})
print('[OK] 线上登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


print()
print('== odk* 模块状态 ==')
mods = ex('ir.module.module', 'search_read',
          [('name', 'like', 'odk%')], ['name', 'state', 'latest_version'], limit=30)
for m in mods:
    print('  %-18s %-12s v%s' % (m['name'], m['state'], m['latest_version']))

print()
print('== odk.dispatch 模型可用性 ==')
for model in ['odk.dispatch', 'odk.dispatch.report', 'odk.dispatch.barcode',
              'odk.dispatch.scan.log']:
    try:
        n = ex(model, 'search_count', [])
        print('  %-24s 可访问，%d 条' % (model, n))
    except Exception as e:
        print('  %-24s 不可访问: %s' % (model, str(e)[:120]))

print()
print('== 关键依赖模块 ==')
for name in ['base', 'web', 'mrp', 'stock', 'odk_wms']:
    r = ex('ir.module.module', 'search_read', [('name', '=', name)],
          ['name', 'state', 'latest_version'], limit=1)
    if r:
        print('  %-10s %-10s v%s' % (r[0]['name'], r[0]['state'], r[0]['latest_version']))
    else:
        print('  %-10s 不存在于模块表' % name)
