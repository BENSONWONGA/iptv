#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# odk_dispatch v2 (条码模块) 线上升级 + 端到端自检
# 前提：服务器已执行 odk_dispatch_fix.sh（模块文件 v20.0.2.0.1 已就位并重启 Odoo）
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


def q(pid):
    return ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']


# ===== 1) 升级模块 v20.0.2.0.1 =====
print()
print('===== [1] 升级 odk_dispatch → v20.0.2.0.1 =====')
ex('ir.module.module', 'update_list')
mid = find('ir.module.module', [('name', '=', 'odk_dispatch')])[0]
st = ex('ir.module.module', 'read', mid, ['state', 'latest_version'])[0]
print('    升级前: %s v%s' % (st['state'], st['latest_version']))
if st['latest_version'] != '20.0.2.0.1':
    ex('ir.module.module', 'button_immediate_upgrade', [mid])
    st = ex('ir.module.module', 'read', mid, ['state', 'latest_version'])[0]
print('    升级后: %s v%s' % (st['state'], st['latest_version']))
assert st['state'] == 'installed' and st['latest_version'] == '20.0.2.0.1'

# ===== 2) 模型恢复 + 新模型可访问 =====
print()
print('===== [2] 模型可用性 =====')
for model in ['odk.dispatch', 'odk.dispatch.report',
              'odk.dispatch.barcode', 'odk.dispatch.barcode.merge',
              'odk.dispatch.scan.log']:
    n = ex(model, 'search_count', [])
    print('    %-28s 可访问，%d 条' % (model, n))

# ===== 3) 端到端：条码生成 → 识别 → 出库 → 入库 → 套码 =====
print()
print('===== [3] 条码端到端自检 =====')
# 测试部件
pids = find('product.product', [('default_code', '=', 'WMS-TEST3')])
if pids:
    pid = pids[0]
    ex('product.product', 'write', [pid], {'active': True})
else:
    pid = ex('product.product', 'create', {
        'name': '条码测试部件', 'default_code': 'WMS-TEST3', 'is_storable': True})
wh = find('stock.warehouse', [], limit=1)[0]
o0 = ex('odk.wms.order', 'create', {
    'doc_type': 'in_purchase', 'warehouse_id': wh, 'note': '条码模块自检备料',
    'line_ids': [(0, 0, {'product_id': pid, 'product_qty': 20.0})]})
ex('odk.wms.order', 'action_confirm', [o0])
print('    [3.1] 备料入库 +20 → 库存=%g' % q(pid))
assert q(pid) == 20

# 派工单 + 生成条码
d = ex('odk.dispatch', 'create', {
    'dispatch_type': 'cutting', 'product_id': pid, 'qty': 10.0,
    'operation': '冲裁', 'user_id': uid, 'note': '条码模块上线自检'})
wz = ex('odk.dispatch.barcode.wizard', 'create', {
    'dispatch_id': d, 'label_qty': 2.0, 'label_count': 3})
ex('odk.dispatch.barcode.wizard', 'action_generate', [wz])
bars = ex('odk.dispatch.barcode', 'search_read',
          [('dispatch_id', '=', d)], ['name', 'qty'], limit=10)
print('    [3.2] 派工单+向导生成 3 张条码: %s' %
      [b['name'] for b in bars])
assert len(bars) == 3

# PDA 识别
code = bars[0]['name']
info = ex('odk.dispatch.barcode', 'act_lookup_barcode', {'code': code})
print('    [3.3] 扫描识别 %s → %s ×%g（派工单 %s）' %
      (code, info['product'], info['qty'], info['dispatch']))
assert info['kind'] == 'barcode' and info['qty'] == 2

# 出库登记 -4（2 张 × 2）
r1 = ex('odk.dispatch.barcode', 'act_register', {
    'code': code, 'action': 'out', 'qty': 4, 'warehouse_id': wh})
print('    [3.4] 部件出库 -4 → 库存=%g | %s' % (q(pid), r1['wms']))
assert q(pid) == 16

# 入库登记 +2
r2 = ex('odk.dispatch.barcode', 'act_register', {
    'code': code, 'action': 'in', 'qty': 2, 'warehouse_id': wh})
print('    [3.5] 部件入库 +2 → 库存=%g | %s' % (q(pid), r2['wms']))
assert q(pid) == 18

# 套码
merge = ex('odk.dispatch.barcode.merge', 'create', {
    'member_ids': [(6, 0, [b['id'] for b in bars])],
    'note': '齐套配送自检'})
mname = ex('odk.dispatch.barcode.merge', 'read', merge, ['name'])[0]['name']
r3 = ex('odk.dispatch.barcode', 'act_register', {
    'code': mname, 'action': 'lookup', 'qty': 0, 'warehouse_id': wh})
print('    [3.6] 套码 %s（%s）' % (mname, r3['message']))
assert r3['kind'] == 'merge' and r3['members'] == 3

# 扫码记录
logs = ex('odk.dispatch.scan.log', 'search_read',
          [('barcode', 'in', [code, mname])],
          ['barcode', 'action', 'qty', 'wms_order_id'], limit=10)
print('    [3.7] 扫码记录留痕 %d 条: %s' %
      (len(logs), [(l['barcode'], l['action']) for l in logs]))
assert len(logs) >= 3

# 报表动作（条码标签/套码标签）
rpts = ex('ir.actions.report', 'search_read',
          [('report_name', 'like', 'odk_dispatch%')], ['name', 'report_name'])
print('    [3.8] 打印报表动作: %s' % [r['name'] for r in rpts])
assert len(rpts) == 2

# 收尾：归档测试物料
ex('product.product', 'write', [pid], {'active': False})
print('    [3.9] 测试部件已归档（条码/扫码记录/单据轨迹保留）')

# ===== 4) PDA 扫码页 HTTP 验证 =====
print()
print('===== [4] PDA 扫码页 /odk/dispatch/scan =====')
import http.cookiejar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
payload = {'jsonrpc': '2.0', 'method': 'call',
           'params': {'db': DB, 'login': USER, 'password': PWD}}
req = urllib.request.Request(URL + '/web/session/authenticate',
                             data=json.dumps(payload).encode(),
                             headers={'Content-Type': 'application/json'})
opener.open(req, timeout=60)
with opener.open(URL + '/odk/dispatch/scan', timeout=60) as resp:
    body = resp.read().decode('utf-8', 'replace')
ok = resp.status == 200 and 'odk-bscan-root' in body
print('    HTTP %s | 页面渲染: %s' % (resp.status, 'OK' if ok else 'FAIL'))
assert ok, 'PDA 扫码页渲染异常'

print()
print('DISPATCH V2 (BARCODE) LIVE UPGRADE SELF-TEST ALL PASS')
