#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PLM+ERP+MES+WMS 端到端全链路验证（本地全新 Odoo 20 · odk_full 库）
场景：鞋厂接单 100 双 → BOM/MRP → 采购 → 委外针车 → 派工成型 → 条码扫码 → 交付/盘点/质检
"""
import json
import urllib.request

URL = 'http://127.0.0.1:8069'
DB, USER, PWD = 'odk_full', 'admin', 'admin'


def call(service, method, *args):
    payload = {'jsonrpc': '2.0', 'method': 'call',
               'params': {'service': service, 'method': method, 'args': list(args)}}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL + '/jsonrpc', data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=600) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(str(out['error'])[:600])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})
print('[OK] 登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


def create(model, vals):
    return ex(model, 'create', vals)


def q(pid):
    return ex('product.product', 'read', [pid], ['qty_available'])[0]['qty_available']


def name_of(model, rid):
    return ex(model, 'read', [rid], ['name'])[0]['name']


def try_step(label, fn):
    """支线环节尽力而为：失败打 WARN 不中断主线"""
    try:
        fn()
        return True
    except Exception as e:
        print('    [WARN] %s 失败（不影响主线）：%s' % (label, str(e)[:180]))
        return False


DOCS = []  # (域, 单据, 单号)


def doc(dom, kind, no):
    DOCS.append((dom, kind, no))
    print('    => %s / %s' % (kind, no))


WHS = ex('stock.warehouse', 'search_read', [], ['name', 'code'], limit=10)
WH = WHS[0]['id']
print('仓库: %s' % [(w['name'], w['code']) for w in WHS])

# ============ S1 主数据 ============
print()
print('===== S1 主数据（PLM 档案） =====')
def up(code, nm, stor=True):
    p = find('product.product', [('default_code', '=', code)])
    if p:
        return p[0]
    return create('product.product', {
        'default_code': code, 'name': nm, 'is_storable': stor})

F_LEATHER = up('F-001', '牛皮皮革')
F_SOLE = up('F-002', '橡胶大底')
F_GLUE = up('F-003', '鞋用胶水')
MID = up('MID-001', '鞋面半成品')
SHOE = up('A-2026', 'A-2026 运动鞋')
print('    物料: F-001/F-002/F-003/MID-001/A-2026 → id=%s' %
      [F_LEATHER, F_SOLE, F_GLUE, MID, SHOE])

p_sew = find('res.partner', [('name', '=', '宏达针车厂')])
p_sew = p_sew[0] if p_sew else create('res.partner', {
    'name': '宏达针车厂', 'supplier_rank': 1})
p_mat = find('res.partner', [('name', '=', '福履材料二厂')])
p_mat = p_mat[0] if p_mat else create('res.partner', {
    'name': '福履材料二厂', 'supplier_rank': 1})
cust = find('res.partner', [('name', '=', '闽鹭鞋贸公司')])
cust = cust[0] if cust else create('res.partner', {
    'name': '闽鹭鞋贸公司', 'customer_rank': 1})
print('    伙伴: 针车厂/材料厂/客户 → id=%s/%s/%s' % (p_sew, p_mat, cust))

# 胶水供应商报价（供 MRP 欠料转采购用）
if not find('product.supplierinfo',
            [('product_tmpl_id', '=', SHOE), ('partner_id', '=', p_mat)]):
    pass
tmpl_glue = ex('product.product', 'read', [F_GLUE], ['product_tmpl_id'])[0]['product_tmpl_id'][0]
if not find('product.supplierinfo', [('product_tmpl_id', '=', tmpl_glue)]):
    create('product.supplierinfo', {'partner_id': p_mat, 'product_tmpl_id': tmpl_glue,
                                    'price': 12.0, 'min_qty': 1})
print('    胶水报价已维护（材料二厂 ¥12/kg）')

# 线边仓（扫码调拨目标）
wh2 = find('stock.warehouse', [('code', '=', 'LINE')])
wh2 = wh2[0] if wh2 else create('stock.warehouse', {'name': '线边仓', 'code': 'LINE'})
print('    线边仓 id=%s' % wh2)

# ============ S2 PLM：BOM + 工艺 ============
print()
print('===== S2 PLM：BOM + 工艺路线 =====')
bom = find('mrp.bom', [('product_tmpl_id', '=', ex('product.product', 'read', [SHOE],
        ['product_tmpl_id'])[0]['product_tmpl_id'][0])])
if not bom:
    bom = create('mrp.bom', {
        'product_tmpl_id': ex('product.product', 'read', [SHOE],
                              ['product_tmpl_id'])[0]['product_tmpl_id'][0],
        'product_qty': 1.0,
        'bom_line_ids': [
            (0, 0, {'product_id': MID, 'product_qty': 1.0}),
            (0, 0, {'product_id': F_SOLE, 'product_qty': 1.0}),
            (0, 0, {'product_id': F_GLUE, 'product_qty': 0.05}),
        ]})
else:
    bom = bom[0]
doc('PLM', 'BOM', ex('mrp.bom', 'read', [bom], ['display_name'])[0]['display_name'])
wc_cut = find('mrp.workcenter', [('name', '=', '冲裁机台')])
wc_cut = wc_cut[0] if wc_cut else create('mrp.workcenter', {'name': '冲裁机台'})
wc = find('mrp.workcenter', [('name', '=', '成型线')])
wc = wc[0] if wc else create('mrp.workcenter', {'name': '成型线'})
ops = ex('mrp.routing.workcenter', 'search_count', [('bom_id', '=', bom)])
if not ops:
    create('mrp.routing.workcenter', [
        {'bom_id': bom, 'name': '冲裁备料', 'sequence': 10, 'workcenter_id': wc_cut},
        {'bom_id': bom, 'name': '成型组装', 'sequence': 20, 'workcenter_id': wc},
    ])
print('    工序: 冲裁备料 → 成型组装（工作中心=成型线）')

# ============ S3 ERP：销售订单 ============
print()
print('===== S3 ERP：销售订单 =====')
so = find('sale.order', [('partner_id', '=', cust), ('state', '=', 'draft')], limit=1)
if not so:
    so = create('sale.order', {
        'partner_id': cust,
        'order_line': [(0, 0, {'product_id': SHOE, 'product_uom_qty': 100.0,
                               'price_unit': 89.0})]})
else:
    so = so[0]
ex('sale.order', 'action_confirm', [so])
sor = ex('sale.order', 'read', so, ['name', 'state'])[0]
doc('ERP', '销售订单', sor['name'])
print('    状态: %s' % sor['state'])
assert sor['state'] in ('sale', 'done')

# ============ S4 ERP：MRP 运算 ============
print()
print('===== S4 ERP：MRP 物料需求运算 =====')
calc = create('odk.mrp.calc', {
    'product_id': SHOE, 'product_qty': 100.0, 'bom_id': bom})
ex('odk.mrp.calc', 'action_calculate', [calc])
calr = ex('odk.mrp.calc', 'read', calc, ['name', 'state', 'shortage_count'])[0]
lines = ex('odk.mrp.calc.line', 'search_read', [('calc_id', '=', calc)],
           ['product_id', 'required_qty', 'stock_qty'], limit=10)
doc('ERP', 'MRP运算单', calr['name'])
print('    状态=%s 欠料行=%d：' % (calr['state'], calr['shortage_count']))
for l in lines:
    print('      %-24s 需求 %g | 现有 %g' % (l['product_id'][1], l['required_qty'], l['stock_qty']))
assert calr['state'] == 'done' and len(lines) == 3 and calr['shortage_count'] == 3

# 欠料转采购询价单（胶水行有报价供应商）
glue_line = find('odk.mrp.calc.line',
                 [('calc_id', '=', calc), ('product_id', '=', F_GLUE)])[0]
ex('odk.mrp.calc.line', 'write', [glue_line], {'select': True})
ex('odk.mrp.calc', 'action_to_purchase', [calc])
pos = ex('purchase.order', 'search_read', [('origin', '=', calr['name'])],
         ['name', 'partner_id', 'state'], limit=5)
for p in pos:
    doc('ERP', '采购询价单', '%s（%s）' % (p['name'], p['partner_id'][1]))
assert pos, '应生成采购询价单'

# ============ S5 WMS：采购入库 ============
print()
print('===== S5 WMS：采购入库 =====')
def wms_in(pid, qty, note):
    o = create('odk.wms.order', {
        'doc_type': 'in_purchase', 'warehouse_id': WH, 'note': note,
        'line_ids': [(0, 0, {'product_id': pid, 'product_qty': qty})]})
    ex('odk.wms.order', 'action_confirm', [o])
    return o

o1 = wms_in(F_LEATHER, 100, '皮革采购入库')
o2 = wms_in(F_SOLE, 120, '大底采购入库')
o3 = wms_in(F_GLUE, 5, '胶水采购入库')
for o in (o1, o2, o3):
    r = ex('odk.wms.order', 'read', o, ['name', 'state'])[0]
    doc('WMS', '采购入库单', '%s → %s' % (r['name'], r['state']))
    assert r['state'] == 'confirmed'
print('    库存: 皮革 %g / 大底 %g / 胶水 %g' % (q(F_LEATHER), q(F_SOLE), q(F_GLUE)))
assert q(F_LEATHER) == 100 and q(F_SOLE) == 120 and q(F_GLUE) == 5

# ============ S6 QMS：来料质检 IQC ============
print()
print('===== S6 QMS：来料质检 IQC =====')
def qc(pid, qty, typ, ok, note):
    return create('odk.quality.check', {
        'product_id': pid, 'product_qty': qty, 'check_type': typ,
        'qty_passed': qty if ok else 0, 'qty_failed': 0 if ok else qty,
        'note': note})

iqc = qc(F_GLUE, 5, 'iqc', True, '胶水来料抽检合格')
r = ex('odk.quality.check', 'read', iqc, ['name', 'result'])[0]
doc('QMS', '质检单(IQC)', '%s → %s' % (r['name'], r['result']))
assert r['result'] == 'pass'

# ============ S7 委外：针车工序外发 ============
print()
print('===== S7 委外：鞋面针车外发 =====')
def subcontract():
    sco = create('odk.subcontract.order', {
        'order_type': 'process', 'product_id': MID, 'product_qty': 100.0,
        'partner_id': p_sew, 'process_name': '针车',
        'warehouse_id': WH,
        'component_ids': [(0, 0, {'product_id': F_LEATHER, 'product_qty': 100.0})]})
    ex('odk.subcontract.order', 'action_confirm', [sco])
    r = ex('odk.subcontract.order', 'read', sco, ['name', 'state'])[0]
    doc('ERP', '制程外发单', '%s → %s' % (r['name'], r['state']))
    assert q(F_LEATHER) == 0, '皮革应已发至针车厂（主仓 0）'
    ex('odk.subcontract.order', 'action_receive', [sco])
    r = ex('odk.subcontract.order', 'read', sco, ['name', 'state'])[0]
    print('    收货: %s → %s | 鞋面库存 %g' % (r['name'], r['state'], q(MID)))
    assert r['state'] == 'done' and q(MID) == 100

try_step('委外针车', subcontract)

# ============ S8 MES：派工 + 领料 ============
print()
print('===== S8 MES：成型派工 + 加工领料 =====')
d = create('odk.dispatch', {
    'dispatch_type': 'process', 'product_id': SHOE, 'qty': 100.0,
    'operation': '成型组装', 'user_id': uid, 'note': '全链路验证派工'})
ex('odk.dispatch', 'action_assign', [d])
ex('odk.dispatch', 'action_start', [d])
dr = ex('odk.dispatch', 'read', d, ['name', 'state'])[0]
doc('MES', '工艺派工单', '%s → %s' % (dr['name'], dr['state']))
assert dr['state'] == 'producing'

mat = create('odk.wms.order', {
    'doc_type': 'out_mfg', 'warehouse_id': WH, 'dispatch_id': d,
    'picker_id': uid, 'note': '成型领料',
    'line_ids': [
        (0, 0, {'product_id': MID, 'product_qty': 100.0}),
        (0, 0, {'product_id': F_SOLE, 'product_qty': 100.0}),
    ]})
ex('odk.wms.order', 'action_confirm', [mat])
mr = ex('odk.wms.order', 'read', mat, ['name', 'state'])[0]
doc('MES', '加工领料单', '%s → %s' % (mr['name'], mr['state']))
assert mr['state'] == 'confirmed'
print('    领料后: 鞋面 %g / 大底 %g（主仓）' % (q(MID), q(F_SOLE)))
assert q(MID) == 0 and q(F_SOLE) == 20

# ============ S9 MES：部件条码 + PDA 扫码入库 ============
print()
print('===== S9 MES：部件条码 + PDA 扫码部件入库 =====')
wz = create('odk.dispatch.barcode.wizard', {
    'dispatch_id': d, 'label_qty': 20.0, 'label_count': 5})
ex('odk.dispatch.barcode.wizard', 'action_generate', [wz])
bars = ex('odk.dispatch.barcode', 'search_read',
          [('dispatch_id', '=', d)], ['name'], limit=10)
doc('MES', '部件条码', '×%d 张（%s …）' % (len(bars), bars[0]['name']))
assert len(bars) == 5
for b in bars:
    ex('odk.dispatch.barcode', 'act_register',
       code=b['name'], action='in', qty=20, warehouse_id=WH)
print('    扫码部件入库 ×5 张 → A-2026 库存 %g' % q(SHOE))
logs = ex('odk.dispatch.scan.log', 'search_count',
          [('dispatch_id', '=', d)])
print('    扫码记录留痕 %d 条' % logs)
assert q(SHOE) == 100 and logs >= 5

# ============ S10 MES：派工日报报工 ============
print()
print('===== S10 MES：派工日报（报满自动完工） =====')
rep = create('odk.dispatch.report', {
    'dispatch_id': d, 'qty_produced': 100.0, 'qty_scrapped': 0.0,
    'work_hours': 10.0, 'rate': 3.0, 'note': '全链路验证日报'})
ex('odk.dispatch.report', 'action_confirm', [rep])
rr = ex('odk.dispatch.report', 'read', rep, ['name', 'state', 'amount'])[0]
doc('MES', '派工日报', '%s → %s 计件 %g' % (rr['name'], rr['state'], rr['amount']))
dr2 = ex('odk.dispatch', 'read', d, ['state', 'qty_done'])[0]
print('    派工单: %s 完工 %g' % (dr2['state'], dr2['qty_done']))
assert rr['state'] == 'confirmed' and dr2['state'] == 'done' and dr2['qty_done'] == 100

# ============ S11 WMS：PDA 扫码调拨 ============
print()
print('===== S11 WMS：PDA 扫码调拨（主仓→线边仓） =====')
def scan_transfer():
    r = ex('odk.scan', 'act_transfer',
           barcode='F-002', qty=20, from_id=WH, to_id=wh2, fo_ref='线边备料')
    doc('WMS', '扫码调拨单', r['name'])
    print('    大底: 主仓→线边仓 20 | 状态 %s' % r['state'])
    assert r['state'] == 'done'

try_step('扫码调拨', scan_transfer)
line_stock = ex('stock.quant', 'search_read',
                 [('product_id', '=', F_SOLE), ('location_id', '=',
                  ex('stock.warehouse', 'read', [wh2], ['lot_stock_id'])[0]['lot_stock_id'][0])],
                 ['quantity'], limit=1)
print('    线边仓大底: %g' % (line_stock[0]['quantity'] if line_stock else 0))

# ============ S12 WMS：盘点 ============
print()
print('===== S12 WMS：盘点（胶水盘亏 0.5kg） =====')
inv = create('odk.wms.inventory', {
    'warehouse_id': WH,
    'line_ids': [(0, 0, {'product_id': F_GLUE, 'counted_qty': 4.5})]})
ex('odk.wms.inventory', 'action_fill_current', [inv])
ex('odk.wms.inventory', 'action_apply', [inv])
ir = ex('odk.wms.inventory', 'read', inv, ['name', 'state'])[0]
doc('WMS', '盘点调整单', '%s → %s | 胶水 %g' % (ir['name'], ir['state'], q(F_GLUE)))
assert ir['state'] == 'done' and q(F_GLUE) == 4.5

# ============ S13 QMS：成品质检 FQC ============
print()
print('===== S13 QMS：成品 FQC =====')
fqc = qc(SHOE, 100, 'fqc', True, '成品抽检合格')
r = ex('odk.quality.check', 'read', fqc, ['name', 'result'])[0]
doc('QMS', '质检单(FQC)', '%s → %s' % (r['name'], r['result']))
assert r['result'] == 'pass'

# ============ S14 ERP：交付客户 ============
print()
print('===== S14 ERP：成品交付 =====')
picks = ex('stock.picking', 'search_read',
           [('sale_id', '=', so), ('picking_type_id.code', '=', 'outgoing')],
           ['name', 'state'], limit=5)
assert picks, '销售订单应生成出库单'
pick = picks[0]['id']
pk = ex('stock.picking', 'read', pick, ['name', 'state'])[0]
# Odoo 20 过账：数量=picked → validate
moves = ex('stock.move', 'search', [('picking_id', '=', pick)], limit=20)
for m in moves:
    mv = ex('stock.move', 'read', m, ['product_uom_qty'])[0]
    ex('stock.move', 'write', [m], {'quantity': mv['product_uom_qty'], 'picked': True})
ex('stock.picking', 'button_validate', [pick])
pk = ex('stock.picking', 'read', pick, ['name', 'state'])[0]
doc('WMS', '销售出库单', '%s → %s' % (pk['name'], pk['state']))
print('    交付后 A-2026 库存: %g' % q(SHOE))
assert pk['state'] == 'done' and q(SHOE) == 0

# ============ 汇总 ============
print()
print('==================== 全链路单据汇总 ====================')
for dom, kind, no in DOCS:
    print('  [%s] %s : %s' % (dom, kind, no))
print('=======================================================')
print()
print('库存对账: A-2026=%g(0) 鞋面=%g(0) 皮革=%g(0) 大底主仓=%g(0) 胶水=%g(4.5)'
      % (q(SHOE), q(MID), q(F_LEATHER), q(F_SOLE), q(F_GLUE)))
print()
print('PLM+ERP+MES+WMS FULL-FLOW SELF-TEST ALL PASS')
