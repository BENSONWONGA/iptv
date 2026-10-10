#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 最小复现：小附件 + create/write 两种方式
import base64
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


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


hello = base64.b64encode(b'hello odk').decode()

# A) create 小附件（位置参数 dict）
a = ex('ir.attachment', 'create', {'name': 't1.txt', 'datas': hello,
                                    'mimetype': 'text/plain', 'public': True})
r = ex('ir.attachment', 'read', [a], ['name', 'file_size', 'datas'])
print('A) create 位置参数:', r)

# B) create 列表参数
b = ex('ir.attachment', 'create', [[{'name': 't2.txt', 'datas': hello,
                                      'mimetype': 'text/plain', 'public': True}]])
r = ex('ir.attachment', 'read', [b], ['name', 'file_size', 'datas'])
print('B) create 列表参数:', r)

# C) write 补 datas 到 221
ex('ir.attachment', 'write', [[221], {'datas': hello}])
r = ex('ir.attachment', 'read', [221], ['file_size', 'datas'])
print('C) write 221:', r)
