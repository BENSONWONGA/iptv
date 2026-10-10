#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 尝试 db_datas 直写 + 下载验证
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
        raise RuntimeError(str(out['error'])[:400])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


hello = base64.b64encode(b'hello odk').decode()

# 看看 ir.attachment 有哪些可用字段
fields = ex('ir.attachment', 'fields_get', [], ['string', 'type', 'store', 'readonly'])
keys = sorted(fields.keys())
print('可用字段:', keys)

# 1) db_datas 直写（绕过 datas inverse）
a = ex('ir.attachment', 'create', {'name': 't3.txt', 'db_datas': hello,
                                    'mimetype': 'text/plain', 'public': True,
                                    'type': 'binary'})
r = ex('ir.attachment', 'read', [a], ['name', 'file_size', 'db_datas', 'type'])
print('t3 记录:', {k: (v[:30] if isinstance(v, str) else v) for k, v in r[0].items()})

# 下载验证（无登录态）
try:
    with urllib.request.urlopen(URL + '/web/content/%s' % a, timeout=30) as resp:
        print('t3 下载: HTTP %s | %d 字节 | %s' % (resp.status, len(resp.read()), resp.read()[:20]))
except urllib.error.HTTPError as e:
    print('t3 下载: HTTP', e.code)
