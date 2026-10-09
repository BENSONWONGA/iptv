#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# odk_mrp_calc 端到端功能测试（本地）
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
        raise RuntimeError(str(out['error'])[:800])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


# 1) 创建运算单：A-001 × 300 双
tids = find('product.template', [('default_code', '=', 'A-001')])
shoe_tid = tids[0]
variants = ex('product.product', 'read',
              find('product.product', [('product_tmpl_id', '=', shoe_tid)], limit=50),
              ['display_name'])
v_id = next((v['id'] for v in variants
             if '黑色' in v['display_name'] and '41' in v['display_name']),
            variants[0]['id'])

calc_id = ex('odk.mrp.calc', 'create', {
    'product_id': v_id, 'product_qty': 300.0})
calc = ex('odk.mrp.calc', 'read', calc_id,
          ['name', 'state', 'bom_id', 'date_run'])[0]
print('[OK] 运算单 %s 创建成功，自动带出 BOM: %s' %
      (calc['name'], calc['bom_id'][1] if calc['bom_id'] else '无'))

# 2) 物料需求计算
res = ex('odk.mrp.calc', 'action_calculate', calc_id)
print('[OK] action_calculate 返回:', str(res)[:120])

lines = ex('odk.mrp.calc.line', 'search_read', [('calc_id', '=', calc_id)],
           ['default_code', 'supplier_id', 'uom_id', 'per_unit_qty',
            'required_qty', 'shortage_qty', 'loss_pct', 'purchase_ratio',
            'suggested_qty', 'ordered_qty', 'unconfirmed_qty', 'stock_qty',
            'free_qty', 'incoming_qty'],
           **{'order': 'default_code'})
print()
print('算料结果（%d 行）:' % len(lines))
for l in lines:
    print('  %-7s 需求 %-8.2f 欠量 %-8.2f 建议 %-8.2f 已订 %-6.2f 未确认 %-6.2f 可用 %-6.2f 厂商=%s'
          % (l['default_code'], l['required_qty'], l['shortage_qty'],
             l['suggested_qty'], l['ordered_qty'], l['unconfirmed_qty'],
             l['free_qty'], l['supplier_id'][1] if l['supplier_id'] else '-'))
assert len(lines) == 9, '应有 9 行材料'
shorts = [l for l in lines if l['shortage_qty'] > 0]
print('欠料行数: %d' % len(shorts))

# 3) 勾选欠料行 → 转采购单
short_ids = [l['id'] for l in shorts]
ex('odk.mrp.calc.line', 'write', short_ids, {'select': True})
res = ex('odk.mrp.calc', 'action_to_purchase', calc_id)
print()
print('[OK] action_to_purchase 返回 domain:', res.get('domain'))

calc = ex('odk.mrp.calc', 'read', calc_id, ['name', 'purchase_order_ids'])[0]
pos = ex('purchase.order', 'read', calc['purchase_order_ids'],
         ['name', 'partner_id', 'origin', 'state', 'amount_untaxed'])
print('生成询价单 %d 张:' % len(pos))
for p in pos:
    print('  %s | %s | 源单=%s | 未税 %.2f' %
          (p['name'], p['partner_id'][1], p['origin'], p['amount_untaxed']))

print()
print('ALL PASS')
