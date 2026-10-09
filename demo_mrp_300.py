#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# MRP 算料演示：A-001 × 300 双
# 流程（对齐旧系统「材料需求计算」逻辑）：
#   BOM 每双用量 → 生产单 300 双自动放大 → 扣可用库存/在途 → 欠料 → 转采购询价单
import json
import sys
import urllib.request

URL = 'http://127.0.0.1:8069'
DB, USER, PWD = 'odoo20', 'admin', 'admin'
QTY = 300.0
LOSS = 0.03  # 采购损耗 3%


def call(service, method, *args, **kw):
    payload = {'jsonrpc': '2.0', 'method': 'call',
               'params': {'service': service, 'method': method, 'args': list(args)}}
    if kw:
        payload['params']['args'] = list(args) + [kw]
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL + '/jsonrpc', data=data,
                                  headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(out['error'].get('message', str(out['error'])[:300]))
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})
print('[OK] 登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


def find_all(model, domain):
    return ex(model, 'search', domain)


# 供应商 + 历史单价（沿用既有采购档案）
SUP_MAP = {
    'M-001': ('鸿达织造', 12.0),
    'M-002': ('鸿达织造', 6.0),
    'M-003': ('恒强底材', 15.0),
    'M-004': ('恒强底材', 8.0),
    'M-005': ('恒强底材', 2.5),
    'M-006': ('鸿达织造', 1.5),
    'M-007': ('鸿达织造', 0.8),
    'M-008': ('恒强底材', 2.2),
    'M-009': ('恒强底材', 30.0),
}
partners = {}
for nm in ('鸿达织造', '恒强底材'):
    ids = find('res.partner', [('name', 'like', nm)])
    assert ids, '供应商不存在: %s' % nm
    partners[nm] = ids[0]

# ============ 第 1 步：BOM 每双用量 ============
shoe_tid = find('product.template', [('default_code', '=', 'A-001')])[0]
bom_id = find('mrp.bom', [('product_tmpl_id', '=', shoe_tid)])[0]
line_ids = find_all('mrp.bom.line', [('bom_id', '=', bom_id)])
lines = ex('mrp.bom.line', 'read', line_ids, ['product_id', 'product_qty', 'uom_id'])

mat_ids = [l['product_id'][0] for l in lines]
prods = {p['id']: p for p in ex('product.product', 'read', mat_ids,
         ['default_code', 'name', 'uom_id', 'qty_available', 'free_qty', 'incoming_qty'])}

print()
print('=' * 92)
print('【第1步】A-001 量产 BOM —— 每双用量（采购算料的依据：先知道一双鞋用多少料）')
print('=' * 92)
print('%-7s %-18s %-6s %8s' % ('材料编号', '材料名称', '单位', '每双用量'))
per_pair = {}
uoms = {}
for l in lines:
    p = prods[l['product_id'][0]]
    uom = (l['uom_id'] or p['uom_id'])[1]
    per_pair[p['default_code']] = l['product_qty']
    uoms[p['default_code']] = uom
    print('%-7s %-18s %-6s %8.2f' % (p['default_code'], p['name'], uom, l['product_qty']))

# ============ 第 2 步：生产单 A-001 × 300 双，BOM 自动展开 ============
variants = ex('product.product', 'read',
              find('product.product', [('product_tmpl_id', '=', shoe_tid)], limit=50),
              ['display_name'])
v_id = next((v['id'] for v in variants
             if '黑色' in v['display_name'] and '41' in v['display_name']),
            variants[0]['id'])

mos = find_all('mrp.production', [('product_id', '=', v_id), ('product_qty', '=', QTY),
                                  ('state', 'in', ['draft', 'confirmed'])])
if mos:
    mo_id = mos[0]
else:
    mo_id = ex('mrp.production', 'create', {
        'product_id': v_id, 'product_qty': QTY, 'bom_id': bom_id})

mo = ex('mrp.production', 'read', mo_id, ['name', 'state', 'move_raw_ids'])[0]
if mo['state'] == 'draft':
    ex('mrp.production', 'action_confirm', mo_id)
    mo = ex('mrp.production', 'read', mo_id, ['name', 'state', 'move_raw_ids'])[0]
print()
print('[OK] 生产订单 %s 已确认（A-001 × %g 双）' % (mo['name'], QTY))

# ============ 第 3 步：算料表 需求=单耗×300，扣可用库存/在途=欠料 ============
moves = ex('stock.move', 'read', mo['move_raw_ids'], ['product_id', 'product_qty'])
print()
print('=' * 92)
print('【第2步】系统自动算料 —— 每双用量 × 300 = 需求，扣可用库存/在途 = 欠料')
print('=' * 92)
print('%-7s %-6s %8s %10s %10s %8s %10s' %
      ('材料编号', '单位', '每双用量', '需求(×300)', '可用库存', '在途', '欠料'))
shorts = []
for m in sorted(moves, key=lambda x: prods[x['product_id'][0]]['default_code']):
    p = prods[m['product_id'][0]]
    code = p['default_code']
    need = m['product_qty']
    free = p['free_qty']
    inc = p['incoming_qty']
    short = max(0.0, need - free - inc)
    print('%-7s %-6s %10.2f %12.2f %12.2f %8.2f %12.2f' %
          (code, uoms[code], per_pair[code], need, free, inc, short))
    if short > 0.0001:
        sup, price = SUP_MAP[code]
        shorts.append((code, short, sup, price, m['product_id'][0]))
print('-' * 92)
print('合计 %d 行材料需求，其中欠料 %d 行' % (len(moves), len(shorts)))

# ============ 第 4 步：欠料 → 转采购询价单（草稿，含 3% 损耗） ============
old = find_all('purchase.order', [('origin', '=', mo['name']), ('state', '=', 'draft')])
if old:
    ex('purchase.order', 'unlink', old)
    print('[OK] 清理旧演示询价单 %d 张' % len(old))

by_sup = {}
for code, short, sup, price, pid in shorts:
    by_sup.setdefault(sup, []).append((code, short, price, pid))

print()
print('=' * 92)
print('【第3步】欠料转采购询价单（数量 = 欠料 × 1.03 损耗；草稿状态待采购确认）')
print('=' * 92)
created = []
for sup, items in sorted(by_sup.items()):
    lines_v = []
    for code, short, price, pid in items:
        qty = round(short * (1 + LOSS) + 1e-9, 2)
        lines_v.append((0, 0, {'product_id': pid, 'product_qty': qty,
                               'price_unit': price}))
        print('  %s → %s × %-8.2f 单价 %-6.2f' % (sup, code, qty, price))
    po_id = ex('purchase.order', 'create', {
        'partner_id': partners[sup], 'origin': mo['name'], 'order_line': lines_v})
    created.append(po_id)
    print('  [OK] 生成询价单 id=%s（供应商：%s，%d 行）' % (po_id, sup, len(lines_v)))
    print()

print('=' * 92)
print('生成的采购询价单：')
for po_id in created:
    po = ex('purchase.order', 'read', po_id, ['name', 'amount_untaxed', 'partner_id'])[0]
    print('  %s | %s | 未税金额 %.2f' % (po['name'], po['partner_id'][1], po['amount_untaxed']))

print()
print('DONE — 浏览器查看：制造 → 操作 → 制造订单 %s → 组件页签；采购 → 订单 → 询价单' % mo['name'])
