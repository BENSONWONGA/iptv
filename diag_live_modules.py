#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 线上模块发现诊断
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


res = ex('ir.module.module', 'update_list')
print('update_list 返回:', res)

mods = ex('ir.module.module', 'search_read', [('name', 'like', 'odk%')],
          ['name', 'state'], limit=30)
print()
print('线上 odk* 模块表:')
for m in mods:
    print('  %-20s %s' % (m['name'], m['state']))

# 精确查
print()
print('精确查 odk_mrp_calc:',
      ex('ir.module.module', 'search', [('name', '=', 'odk_mrp_calc')], limit=5))
