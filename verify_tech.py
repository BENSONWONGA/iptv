# -*- coding: utf-8 -*-
import json
import urllib.request

URL = 'http://127.0.0.1:8069'


def call(service, method, *args):
    payload = {'jsonrpc': '2.0', 'method': 'call',
               'params': {'service': service, 'method': method, 'args': list(args)}}
    req = urllib.request.Request(
        URL + '/jsonrpc', data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    out = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    if 'error' in out:
        raise RuntimeError(out['error']['data'].get('message', '?')[:150])
    return out['result']


uid = call('common', 'authenticate', 'odoo20', 'admin', 'admin', {})


def ex(model, method, *args, **kw):
    return call('object', 'execute_kw', 'odoo20', uid, 'admin',
                model, method, list(args), kw)


print('===== 最终验证 =====')
print('登录: uid =', uid)
print('技转模型数:', ex('ir.model', 'search_count', [('model', 'like', 'odk.tech')]))
for c in ex('odk.tech.confirm', 'search_read', [], ['name', 'state'], limit=5):
    print('  确认单:', c['name'], '| 状态:', c['state'])
for r in ex('odk.tech.routing', 'search_read', [], ['name'], limit=5):
    print('  工艺流程单:', r['name'])
print('  工序行数:', ex('odk.tech.routing.line', 'search_count', []))
for t in ex('odk.tech.trial', 'search_read', [], ['name', 'state', 'product_qty'], limit=5):
    print('  试做单:', t['name'], '| 状态:', t['state'], '| 数量:', t['product_qty'])
for p in ex('odk.tech.progress', 'search_read', [], ['name', 'stage'], limit=5):
    print('  进度:', p['name'], '| 阶段:', p['stage'])
print('技转管理菜单存在:', bool(ex('ir.ui.menu', 'search', [('name', '=', '技转管理')])))
print('VERIFIED')
