#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# odk_subcontract v2 本地升级 + 端到端测试
import datetime
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
    with urllib.request.urlopen(req, timeout=600) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(str(out['error'])[:900])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})
print('[OK] 登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


# ---------- 1) 升级 odk_subcontract 到 v2 ----------
ex('ir.module.module', 'update_list')
mid = find('ir.module.module', [('name', '=', 'odk_subcontract')])[0]
ex('ir.module.module', 'button_immediate_upgrade', [mid])
mod = ex('ir.module.module', 'read', mid, ['state', 'latest_version'])[0]
print('[OK] odk_subcontract 升级完成: %s v%s' % (mod['state'], mod['latest_version']))

# 新模型可用
print('[OK] odk.subcontract.quote 可访问，现有报价 %d 条' %
      ex('odk.subcontract.quote', 'search_count', []))

# ---------- 2) 制程工艺报价 ----------
pids = find('res.partner', [('name', 'like', '宏达针车厂')])
if pids:
    partner = pids[0]
else:
    partner = ex('res.partner', 'create',
                 {'name': '宏达针车厂', 'supplier_rank': 1})
    print('[OK] 新建供应商 宏达针车厂 id=%s' % partner)

shoe_tid = find('product.template', [('default_code', '=', 'A-001')])[0]
variants = ex('product.product', 'read',
              find('product.product', [('product_tmpl_id', '=', shoe_tid)], limit=50),
              ['display_name'])
v_id = next((v['id'] for v in variants
             if '黑色' in v['display_name'] and '41' in v['display_name']),
            variants[0]['id'])
bom_id = find('mrp.bom', [('product_tmpl_id', '=', shoe_tid)])[0]
wh_id = find('stock.warehouse', [], limit=1)[0]

quote_id = ex('odk.subcontract.quote', 'create', {
    'partner_id': partner,
    'process_name': '针车',
    'price_unit': 15.0,
    'product_id': v_id,
    'date_valid_to': (datetime.date.today() + datetime.timedelta(days=60)).isoformat(),
})
ex('odk.subcontract.quote', 'action_confirm', [quote_id])
q = ex('odk.subcontract.quote', 'read', quote_id, ['name', 'state', 'price_unit'])[0]
print('[OK] 工艺报价 %s（%s）针车 @%.2f 已确认' % (q['name'], q['state'], q['price_unit']))

# ---------- 3) 制程外发加工单（关联报价，交期设为昨天 → 应超期） ----------
yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
order_id = ex('odk.subcontract.order', 'create', {
    'order_type': 'process',
    'process_name': '针车',
    'quote_id': quote_id,
    'partner_id': partner,
    'warehouse_id': wh_id,
    'product_id': v_id,
    'product_qty': 50.0,
    'bom_id': bom_id,
    'price_unit': 15.0,
    'date_due': yesterday,
})
ex('odk.subcontract.order', 'action_fill_components', [order_id])
ex('odk.subcontract.order', 'action_confirm', [order_id])
o = ex('odk.subcontract.order', 'read', order_id,
       ['name', 'state', 'order_type', 'process_name', 'date_sent',
        'is_overdue', 'days_overdue', 'component_count'])[0]
print('[OK] 制程外发单 %s 已发料: 组件 %d 行, 发料日期=%s' %
      (o['name'], o['component_count'], o['date_sent'][:16] if o['date_sent'] else '无'))
assert o['state'] == 'confirmed' and o['is_overdue'] and o['days_overdue'] >= 1, \
    '超期计算异常: %s' % o
print('     超期预警 ✓ (超期 %d 天)' % o['days_overdue'])

# ---------- 4) 补耗加工单（关联来源单） ----------
sup_id = ex('odk.subcontract.order', 'create', {
    'order_type': 'loss',
    'process_name': '针车',
    'supplement_of_id': order_id,
    'partner_id': partner,
    'warehouse_id': wh_id,
    'product_id': v_id,
    'product_qty': 5.0,
    'bom_id': bom_id,
    'price_unit': 0.0,
    'note': '针车工序损耗补料',
})
ex('odk.subcontract.order', 'action_fill_components', [sup_id])
ex('odk.subcontract.order', 'action_confirm', [sup_id])
s = ex('odk.subcontract.order', 'read', sup_id,
       ['name', 'state', 'supplement_of_id', 'component_count'])[0]
print('[OK] 补耗单 %s 已发料: 来源=%s, 组件 %d 行' %
      (s['name'], s['supplement_of_id'][1], s['component_count']))

# 来源单上的补耗计数
src = ex('odk.subcontract.order', 'read', order_id, ['supplement_count'])[0]
assert src['supplement_count'] == 1
print('     来源单补耗计数 ✓ (1)')

# ---------- 5) 收货闭环 ----------
ex('odk.subcontract.order', 'action_receive', [order_id])
ex('odk.subcontract.order', 'action_receive', [sup_id])
o2 = ex('odk.subcontract.order', 'read', order_id,
        ['state', 'date_received', 'is_overdue'])[0]
s2 = ex('odk.subcontract.order', 'read', sup_id, ['state', 'date_received'])[0]
print('[OK] 制程单收货完成: %s 回仓=%s' %
      (o2['state'], o2['date_received'][:16] if o2['date_received'] else '无'))
print('[OK] 补耗单收货完成: %s' % s2['state'])
assert o2['state'] == 'done' and s2['state'] == 'done'
assert not o2['is_overdue'], '收货后不应再超期'

# ---------- 6) 部件配套欠数查询数据就绪 ----------
short_cnt = ex('odk.mrp.calc.line', 'search_count', [('shortage_qty', '>', 0)])
print('[OK] 部件配套欠数查询: 欠料行 %d 条（来自 MRP-0001 运算）' % short_cnt)

# ---------- 7) 外采指令单 ----------
wc_id = ex('odk.subcontract.order', 'create', {
    'order_type': 'purchase',
    'partner_id': partner,
    'warehouse_id': wh_id,
    'product_id': v_id,
    'product_qty': 30.0,
    'bom_id': bom_id,
    'price_unit': 8.0,
    'note': '带料外采指令',
})
w = ex('odk.subcontract.order', 'read', wc_id, ['name', 'state', 'order_type'])[0]
print('[OK] 外采指令单 %s（草稿）✓' % w['name'])

print()
print('ALL PASS')
