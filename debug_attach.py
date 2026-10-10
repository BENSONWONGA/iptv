#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 调试线上附件 221 的存储与访问
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


r = ex('ir.attachment', 'read', [221],
       ['name', 'file_size', 'mimetype', 'public', 'type', 'store_fname', 'url'])
print('附件记录:', json.dumps(r, ensure_ascii=False, indent=1))

# 带登录态的下载（jsonrpc 登录拿 session cookie）
import http.cookiejar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
payload = {'jsonrpc': '2.0', 'method': 'call',
           'params': {'db': DB, 'login': USER, 'password': PWD}}
req = urllib.request.Request(URL + '/web/session/authenticate',
                              data=json.dumps(payload).encode(),
                              headers={'Content-Type': 'application/json'})
opener.open(req, timeout=60)
with opener.open(URL + '/web/content/221?download=true', timeout=60) as resp:
    body = resp.read()
print('带登录下载: HTTP %s | %d 字节 | 前 80 字节: %s'
      % (resp.status, len(body), body[:80]))
