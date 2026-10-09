#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 本地安装 odk_mrp_calc 模块
import json
import urllib.request

URL = 'http://127.0.0.1:8069'
DB, USER, PWD = 'odoo20', 'admin', 'admin'


def call(service, method, *args):
    payload = {'jsonrpc': '2.0', 'method': 'call',
               'params': {'service': service, 'method': method, 'args': list(args)}}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL + '/jsonrpc', data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(str(out['error'])[:500])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})
print('[OK] 本地登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


# 1) 重扫 addons 目录
res = ex('ir.module.module', 'update_list')
print('[OK] update_list:', res)

# 2) 找到模块并安装
mids = ex('ir.module.module', 'search', [('name', '=', 'odk_mrp_calc')])
if not mids:
    print('!! 未发现 odk_mrp_calc，请确认 addons 路径')
    raise SystemExit(1)
mod = ex('ir.module.module', 'read', mids, ['name', 'state'])[0]
print('模块状态: %s (id=%s)' % (mod['state'], mids[0]))
if mod['state'] != 'installed':
    ex('ir.module.module', 'button_immediate_install', mids)
    mod = ex('ir.module.module', 'read', mids, ['name', 'state'])[0]
    print('[OK] 安装完成，状态:', mod['state'])

# 3) 验证模型可访问
cnt = ex('odk.mrp.calc', 'search_count', [])
print('[OK] odk.mrp.calc 可访问，当前 %d 张运算单' % cnt)
