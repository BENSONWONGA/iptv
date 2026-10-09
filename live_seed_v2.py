#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 线上演示数据：MRP运算单 + 工艺报价 + 制程外发单 + 外采指令单
import datetime
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


# 0) 基础引用
shoe_tid = find('product.template', [('default_code', '=', 'A-001')])[0]
variants = ex('product.product', 'read',
              find('product.product', [('product_tmpl_id', '=', shoe_tid)], limit=50),
              ['display_name'])
v_id = next((v['id'] for v in variants
             if '黑色' in v['display_name'] and '40' in v['display_name']),
            variants[0]['id'])
bom_id = find('mrp.bom', [('product_tmpl_id', '=', shoe_tid)])[0]
wh_id = find('stock.warehouse', [], limit=1)[0]
pids = find('res.partner', [('name', 'like', '宏达针车厂')])
partner = pids[0] if pids else None
print('[OK] A-001 变体 id=%s, BOM id=%s, 仓库 id=%s, 宏达针车厂=%s' %
      (v_id, bom_id, wh_id, partner))

# 1) MRP 运算单（A-001 × 300）——部件配套欠数查询的数据源
calc_id = ex('odk.mrp.calc', 'create', {
    'product_id': v_id, 'product_qty': 300.0})
ex('odk.mrp.calc', 'action_calculate', calc_id)
calc = ex('odk.mrp.calc', 'read', calc_id, ['name', 'state', 'shortage_count'])[0]
print('[OK] MRP 运算单 %s（%s）：%d 行欠料' %
      (calc['name'], calc['state'], calc['shortage_count']))
lines = ex('odk.mrp.calc.line', 'search_read', [('calc_id', '=', calc_id)],
           ['default_code', 'shortage_qty', 'suggested_qty'])
for l in lines:
    if l['shortage_qty'] > 0:
        print('     欠料: %s 欠 %g, 建议 %g' %
              (l['default_code'], l['shortage_qty'], l['suggested_qty']))

# 2) 制程工艺报价（针车 @15）
if not ex('odk.subcontract.quote', 'search_count', []):
    quote_id = ex('odk.subcontract.quote', 'create', {
        'partner_id': partner,
        'process_name': '针车',
        'price_unit': 15.0,
        'product_id': v_id,
        'date_valid_to': (datetime.date.today() + datetime.timedelta(days=90)).isoformat(),
    })
    ex('odk.subcontract.quote', 'action_confirm', [quote_id])
    q = ex('odk.subcontract.quote', 'read', quote_id, ['name', 'state'])[0]
    print('[OK] 工艺报价 %s（%s）针车 @15.00' % (q['name'], q['state']))
else:
    quote_id = find('odk.subcontract.quote', [], limit=1)[0]
    print('[OK] 已有报价，复用 id=%s' % quote_id)

# 3) 制程外发加工单（关联报价，草稿状态，不动库存）
order_id = ex('odk.subcontract.order', 'create', {
    'order_type': 'process',
    'process_name': '针车',
    'quote_id': quote_id,
    'partner_id': partner,
    'warehouse_id': wh_id,
    'product_id': v_id,
    'product_qty': 100.0,
    'bom_id': bom_id,
    'price_unit': 15.0,
    'date_due': (datetime.date.today() + datetime.timedelta(days=10)).isoformat(),
})
ex('odk.subcontract.order', 'action_fill_components', [order_id])
o = ex('odk.subcontract.order', 'read', order_id,
       ['name', 'state', 'order_type', 'component_count'])[0]
print('[OK] 制程外发单 %s（%s, 类型=%s）: %d 行组件（草稿）' %
      (o['name'], o['state'], o['order_type'], o['component_count']))

# 4) 外采指令单（草稿）
wc_id = ex('odk.subcontract.order', 'create', {
    'order_type': 'purchase',
    'partner_id': partner,
    'warehouse_id': wh_id,
    'product_id': v_id,
    'product_qty': 50.0,
    'bom_id': bom_id,
    'price_unit': 8.0,
    'note': '带料外采指令（示例）',
})
w = ex('odk.subcontract.order', 'read', wc_id, ['name', 'state', 'order_type'])[0]
print('[OK] 外采指令单 %s（%s, 类型=%s）' % (w['name'], w['state'], w['order_type']))

print()
print('LIVE SEED DONE')
