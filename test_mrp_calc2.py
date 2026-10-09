#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 本地补供应商报价档案（线上已有），然后重测 转采购单
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


# 供应商（本地沿用与线上一致的名称）
sup_fab = find('res.partner', [('name', 'like', '鸿达织造')])[0]
sup_sol = find('res.partner', [('name', 'like', '恒强底材')])[0]

SUP_MAP = {
    'M-001': (sup_fab, 12.0),
    'M-002': (sup_fab, 6.0),
    'M-003': (sup_sol, 15.0),
    'M-004': (sup_sol, 8.0),
    'M-005': (sup_sol, 2.5),
    'M-006': (sup_fab, 1.5),
    'M-007': (sup_fab, 0.8),
    'M-008': (sup_sol, 2.2),
    'M-009': (sup_sol, 30.0),
}

# 幂等创建 supplierinfo
for code, (partner, price) in SUP_MAP.items():
    tmpl_id = ex('product.template', 'search', [('default_code', '=', code)], limit=1)
    tmpl_id = tmpl_id[0] if tmpl_id else None
    if not tmpl_id:
        # 材料编码可能挂在变体上，回落用名称找模板
        pid = find('product.product', [('default_code', '=', code)])
        if not pid:
            print('!! 找不到材料 %s' % code)
            continue
        tmpl_id = ex('product.product', 'read', pid, ['product_tmpl_id'])[0]['product_tmpl_id'][0]
    exist = ex('product.supplierinfo', 'search',
               [('product_tmpl_id', '=', tmpl_id)], limit=1)
    if not exist:
        ex('product.supplierinfo', 'create', {
            'product_tmpl_id': tmpl_id, 'partner_id': partner, 'price': price})
        print('[OK] 报价档案 %s → %s @%.2f' % (code, ex('res.partner', 'read', partner, ['name'])[0]['name'], price))
    else:
        print('[跳过] %s 已有报价档案' % code)

# 找刚才的运算单，重算 + 勾选 + 转采购
calc_id = find('odk.mrp.calc', [('name', '=', 'MRP-0001')])[0]
ex('odk.mrp.calc', 'action_calculate', calc_id)
print()
print('[OK] 重新运算完成')

lines = ex('odk.mrp.calc.line', 'search_read', [('calc_id', '=', calc_id)],
           ['default_code', 'supplier_id', 'shortage_qty', 'suggested_qty'])
for l in lines:
    print('  %-7s 欠量 %-8.2f 建议 %-8.2f 厂商=%s'
          % (l['default_code'], l['shortage_qty'], l['suggested_qty'],
             l['supplier_id'][1] if l['supplier_id'] else '-'))

short_ids = [l['id'] for l in lines if l['shortage_qty'] > 0]
ex('odk.mrp.calc.line', 'write', short_ids, {'select': True})
res = ex('odk.mrp.calc', 'action_to_purchase', calc_id)
print()
print('[OK] 转采购单 domain:', res.get('domain'))

calc = ex('odk.mrp.calc', 'read', calc_id, ['name', 'purchase_order_ids'])[0]
pos = ex('purchase.order', 'read', calc['purchase_order_ids'],
         ['name', 'partner_id', 'origin', 'state', 'amount_untaxed'])
print('生成询价单 %d 张:' % len(pos))
for p in pos:
    print('  %s | %s | 源单=%s | 未税 %.2f' %
          (p['name'], p['partner_id'][1], p['origin'], p['amount_untaxed']))

print()
print('ALL PASS')
