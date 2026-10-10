#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 线上同步健康检查：除 odk_dispatch 外的模块业务可用性 + PDA 页面状态
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
        raise RuntimeError(str(out['error'])[:300])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})
print('[OK] 线上登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


print()
print('== 已上线模块业务数据健康度 ==')
for model, label in [
        ('odk.wms.order', '仓库管理·业务单'),
        ('odk.wms.inventory', '仓库管理·盘点单'),
        ('odk.mrp.calc', 'MRP运算单'),
        ('odk.subcontract.order', '委外加工单'),
        ('odk.subcontract.quote', '工艺报价'),
        ('odk.quality.check', '质检单'),
        ('odk.scan', '扫码出入库(接口)')]:
    try:
        n = ex(model, 'search_count', [])
        print('  %-24s %s: %d 条 ✓' % (model, label, n))
    except Exception as e:
        print('  %-24s %s: 不可访问 ✗ %s' % (model, label, str(e)[:80]))

print()
print('== PDA 页面路由状态 ==')
for path in ['/odk/scan', '/odk/dispatch/scan']:
    try:
        urllib.request.urlopen(URL + path, timeout=20)
        print('  %-22s HTTP 200（需登录跳转后可访问）' % path)
    except urllib.error.HTTPError as e:
        print('  %-22s HTTP %d %s' % (path, e.code,
              '（未注册：odk_dispatch 未加载）' if 'dispatch' in path else ''))
    except Exception as e:
        print('  %-22s 异常: %s' % (path, str(e)[:60]))
