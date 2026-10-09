#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 奥登科鞋业 · Odoo 20 基础档案一键配置（幂等，可重复执行）
import json
import sys
import urllib.request

URL = 'http://220.162.99.166:88'
DB, USER, PWD = 'odk_erp', 'admin', 'admin'


def call(service, method, *args, **kw):
    payload = {
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'service': service, 'method': method, 'args': list(args)},
    }
    if kw:
        payload['params']['args'] = list(args) + [kw]
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        URL + '/jsonrpc', data=data,
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(out['error'].get('message', str(out['error'])[:200]))
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})
if not uid:
    print('AUTH_FAILED')
    sys.exit(1)
print('[OK] 登录成功 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


def find(model, domain, limit=1):
    return ex(model, 'search', domain, limit=limit)


def fields_of(model):
    return ex(model, 'fields_get', [], {'attributes': ['string']})


# ---------- 1) 产品分类：材料类型 + 鞋款类型 ----------
root = find('product.category', [('parent_id', '=', False)])[0]


def ensure_cat(name, parent):
    ids = find('product.category', [('name', '=', name), ('parent_id', '=', parent)])
    if ids:
        return ids[0]
    return ex('product.category', 'create', {'name': name, 'parent_id': parent})


cat_chengpin = ensure_cat('成品鞋', root)
cat_nan = ensure_cat('男鞋', cat_chengpin)
cat_nv = ensure_cat('女鞋', cat_chengpin)
cat_mianliao = ensure_cat('面料', root)
cat_dicai = ensure_cat('底材', root)
cat_fuliao = ensure_cat('辅料', root)
cat_baocai = ensure_cat('包材', root)
cat_huagong = ensure_cat('化工', root)
print('[OK] 产品分类 8 个（材料类型5 + 鞋款：成品鞋/男鞋/女鞋）')

# ---------- 2) 计量单位（Odoo20 相对参考单位制，中文名挂到基准单位上） ----------
def base_uom(en_name):
    ids = find('uom.uom', [('name', '=', en_name)])
    return ids[0] if ids else False


def ensure_uom(cn_name, ref_name):
    ids = find('uom.uom', [('name', '=', cn_name)])
    if ids:
        return ids[0]
    ref = base_uom(ref_name) if ref_name else False
    return ex('uom.uom', 'create', {
        'name': cn_name, 'relative_factor': 1.0, 'relative_uom_id': ref})


uom_units_base = base_uom('Units') or base_uom('Units') or False
uom_shuang = ensure_uom('双', 'Units')
uom_unit = ensure_uom('个', 'Units')
uom_mi = ensure_uom('米', 'm')
uom_kg = ensure_uom('千克', 'kg')
print('[OK] 计量单位：双 / 个 / 米 / 千克（中文名，挂基准单位）')

# ---------- 3) 颜色 + 尺码 属性（材料颜色/成品颜色） ----------
attr_fields = fields_of('product.attribute')
has_variant_flag = 'create_variant' in attr_fields


def ensure_attr(name):
    ids = find('product.attribute', [('name', '=', name)])
    if ids:
        return ids[0]
    vals = {'name': name}
    if has_variant_flag:
        vals['create_variant'] = 'always'
    return ex('product.attribute', 'create', vals)


def ensure_attr_val(attr_id, name):
    ids = find('product.attribute.value', [('name', '=', name), ('attribute_id', '=', attr_id)])
    if ids:
        return ids[0]
    return ex('product.attribute.value', 'create', {'name': name, 'attribute_id': attr_id})


attr_color = ensure_attr('颜色')
color_ids = [ensure_attr_val(attr_color, n) for n in ['黑色', '白色', '灰色']]
attr_size = ensure_attr('尺码')
size_ids = [ensure_attr_val(attr_size, n) for n in ['40', '41', '42', '43', '44']]
print('[OK] 属性：颜色(黑/白/灰) + 尺码(40-44)')

# ---------- 4) 材料档案 ----------
pt_fields = fields_of('product.template')
type_selection = pt_fields.get('type', {}).get('selection', [])
type_vals = [v[0] for v in type_selection] if type_selection else []
if 'product' in type_vals:
    prod_type = 'product'
elif 'consu' in type_vals:
    prod_type = 'consu'
else:
    prod_type = None


def ensure_product(name, code, categ, uom, cost, is_sale=False, price=0.0, attrs=None):
    ids = find('product.template', [('default_code', '=', code)])
    if ids:
        return ids[0]
    vals = {
        'name': name, 'default_code': code, 'categ_id': categ, 'uom_id': uom,
        'standard_price': cost, 'purchase_ok': not is_sale, 'sale_ok': is_sale,
    }
    if prod_type:
        vals['type'] = prod_type
    if is_sale:
        vals['list_price'] = price
    if attrs:
        vals['attribute_line_ids'] = attrs
    return ex('product.template', 'create', vals)


materials = [
    ('飞织鞋面', 'M-001', cat_mianliao, uom_shuang, 18.0),
    ('网布内里', 'M-002', cat_mianliao, uom_mi, 6.0),
    ('橡胶大底', 'M-003', cat_dicai, uom_shuang, 12.0),
    ('EVA中底', 'M-004', cat_dicai, uom_shuang, 8.0),
    ('记忆棉鞋垫', 'M-005', cat_fuliao, uom_shuang, 3.0),
    ('涤纶鞋带', 'M-006', cat_fuliao, uom_unit, 1.5),
    ('涤纶车线', 'M-007', cat_fuliao, uom_mi, 0.8),
    ('鞋盒', 'M-008', cat_baocai, uom_unit, 2.0),
    ('环保胶水', 'M-009', cat_huagong, uom_kg, 15.0),
]
mats = {}
for name, code, cat, uom, cost in materials:
    mats[code] = ensure_product(name, code, cat, uom, cost)
print('[OK] 材料档案 9 个（面料2/底材2/辅料3/包材1/化工1）')

# ---------- 5) 成品档案（鞋商品信息，颜色×尺码出变体） ----------
attr_lines = [
    (0, 0, {'attribute_id': attr_color, 'value_ids': [(6, 0, [color_ids[0], color_ids[2]])]}),
    (0, 0, {'attribute_id': attr_size, 'value_ids': [(6, 0, size_ids)]}),
]
shoe_tid = ensure_product('A-001 男士轻便跑步鞋', 'A-001', cat_nan, uom_shuang,
                           60.0, is_sale=True, price=129.0, attrs=attr_lines)
variants = find('product.product', [('product_tmpl_id', '=', shoe_tid)], limit=100)
print('[OK] 成品 A-001 男士轻便跑步鞋，生成变体 %d 个（2色x5码）' % len(variants))

# ---------- 6) 客户档案 + 厂商档案 ----------
partner_fields = fields_of('res.partner')


def ensure_partner(name, kind):
    ids = find('res.partner', [('name', '=', name), ('is_company', '=', True)])
    if ids:
        return ids[0]
    vals = {'name': name, 'is_company': True}
    if kind == 'customer':
        if 'customer_rank' in partner_fields:
            vals['customer_rank'] = 1
        if 'customer' in partner_fields:
            vals['customer'] = True
    else:
        if 'supplier_rank' in partner_fields:
            vals['supplier_rank'] = 1
        if 'supplier' in partner_fields:
            vals['supplier'] = True
    return ex('res.partner', 'create', vals)


cust1 = ensure_partner('福州华峰鞋业连锁', 'customer')
sup1 = ensure_partner('晋江鸿达织造(面料)', 'supplier')
sup2 = ensure_partner('莆田恒强底材(大底)', 'supplier')
print('[OK] 客户1个 + 厂商2个')

# ---------- 7) 付款方式 + 税点（尽力而为） ----------
try:
    if not find('account.payment.term', [('name', '=', '月结30天')]):
        ex('account.payment.term', 'create', {
            'name': '月结30天',
            'line_ids': [(0, 0, {'value': 'percent', 'value_amount': 100,
                                 'days': 30, 'option': 'day_after_invoice_date'})]})
    print('[OK] 付款条件：月结30天')
except Exception as e:
    print('[跳过] 付款条件:', str(e)[:100])

for use in ('purchase', 'sale'):
    try:
        if not find('account.tax', [('name', 'like', '13%'), ('type_tax_use', '=', use)]):
            ex('account.tax', 'create', {
                'name': '增值税13%', 'amount_type': 'percent',
                'amount': 13, 'type_tax_use': use})
        print('[OK] 税点 13%% (%s)' % use)
    except Exception as e:
        print('[跳过] 税点 %s:' % use, str(e)[:100])

# ---------- 8) 示例 BOM（A-001 每双用量） ----------
bom_fields = fields_of('mrp.bom')
line_fields = fields_of('mrp.bom.line')
line_uom_f = 'uom_id' if 'uom_id' in line_fields else (
    'product_uom_id' if 'product_uom_id' in line_fields else None)
bom_uom_f = 'uom_id' if 'uom_id' in bom_fields else (
    'product_uom_id' if 'product_uom_id' in bom_fields else None)
type_f = 'type' if 'type' in bom_fields else 'bom_type'


def variant_of(tid):
    return find('product.product', [('product_tmpl_id', '=', tid)])[0]


bom_spec = [
    ('M-001', 1.0, uom_shuang),
    ('M-002', 1.2, uom_mi),
    ('M-003', 1.0, uom_shuang),
    ('M-004', 1.0, uom_shuang),
    ('M-005', 1.0, uom_shuang),
    ('M-006', 1.0, uom_unit),
    ('M-007', 3.0, uom_mi),
    ('M-008', 1.0, uom_unit),
    ('M-009', 0.05, uom_kg),
]
bom_ids = find('mrp.bom', [('product_tmpl_id', '=', shoe_tid)])
if bom_ids:
    print('[OK] BOM 已存在 id=%s' % bom_ids[0])
else:
    lines = []
    for code, qty, uom in bom_spec:
        lv = {'product_id': variant_of(mats[code]), 'product_qty': qty}
        if line_uom_f:
            lv[line_uom_f] = uom
        lines.append((0, 0, lv))
    bvals = {'product_tmpl_id': shoe_tid, 'product_qty': 1.0, 'bom_line_ids': lines}
    if bom_uom_f:
        bvals[bom_uom_f] = uom_shuang
    if type_f in bom_fields:
        bvals[type_f] = 'normal'
    bid = ex('mrp.bom', 'create', bvals)
    print('[OK] BOM 新建 id=%s（9行材料用量）' % bid)

# ---------- 9) 汇总验证 ----------
print('\n========== 配置结果汇总 ==========')
print('产品模板总数: %s' % ex('product.template', 'search_count', []))
print('A-001 变体数: %s' % ex('product.product', 'search_count', [('product_tmpl_id', '=', shoe_tid)]))
bid = find('mrp.bom', [('product_tmpl_id', '=', shoe_tid)])
if bid:
    line_ids = find('mrp.bom.line', [('bom_id', '=', bid[0])], limit=50)
    data = ex('mrp.bom.line', 'read', line_ids, ['product_id', 'product_qty'])
    print('BOM 明细 (%d 行):' % len(data))
    for l in data:
        print('   - %s x %s' % (l['product_id'][1], l['product_qty']))
print('公司类合作伙伴: %s' % ex('res.partner', 'search_count', [('is_company', '=', True)]))
print('DONE')
