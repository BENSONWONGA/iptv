#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 线上模块安装/升级：odk_mrp_calc（新装）+ odk_subcontract（升级 v2）
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


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


# 1) 重扫模块
print('[1] update_list ...')
ex('ir.module.module', 'update_list')

# 2) 安装 odk_mrp_calc
mid = find('ir.module.module', [('name', '=', 'odk_mrp_calc')])[0]
st = ex('ir.module.module', 'read', mid, ['state'])[0]['state']
print('[2] odk_mrp_calc 状态: %s' % st)
if st != 'installed':
    ex('ir.module.module', 'button_immediate_install', [mid])
    st = ex('ir.module.module', 'read', mid, ['state', 'latest_version'])[0]
    print('    安装完成: %s v%s' % (st['state'], st['latest_version']))
cnt = ex('odk.mrp.calc', 'search_count', [])
print('    odk.mrp.calc 可访问，现有 %d 张运算单' % cnt)

# 3) 升级 odk_subcontract 到 v2
mid2 = find('ir.module.module', [('name', '=', 'odk_subcontract')])[0]
ex('ir.module.module', 'button_immediate_upgrade', [mid2])
st2 = ex('ir.module.module', 'read', mid2, ['state', 'latest_version'])[0]
print('[3] odk_subcontract 升级完成: %s v%s' % (st2['state'], st2['latest_version']))

# 4) 验证新模型与菜单
qc = ex('odk.subcontract.quote', 'search_count', [])
print('[4] odk.subcontract.quote 可访问，现有 %d 条报价' % qc)
orders = ex('odk.subcontract.order', 'search_read', [],
            ['name', 'state', 'order_type'], **{'limit': 10, 'order': 'id desc'})
for o in orders:
    print('    %-14s %-10s 类型=%s' % (o['name'], o['state'], o['order_type'] or '(默认)'))

print()
print('LIVE INSTALL DONE')
