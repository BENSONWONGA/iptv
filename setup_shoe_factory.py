# 鞋业加工厂主数据初始化脚本（幂等，可重复执行）
# 用法: echo "exec(open('/opt/odoo20/setup_shoe_factory.py').read())" | odoo-bin shell -c conf -d benson --no-http

env = env  # noqa

def get_or_create(model, domain, vals):
    rec = env[model].search(domain, limit=1)
    if not rec:
        rec = env[model].create(vals)
    return rec

# ============ 1. 计量单位：双 ============
uom_pair = get_or_create('uom.uom', [('name', '=', '双')], {
    'name': '双', 'relative_factor': 1.0, 'active': True})
uom_m = env.ref('uom.product_uom_meter')
uom_kg = env.ref('uom.product_uom_kgm')
uom_unit = env.ref('uom.product_uom_unit')

# ============ 2. 产品分类 ============
cat_map = {}
for name in ['面料', '底材', '辅料', '包装材料', '半成品', '成品鞋']:
    cat_map[name] = get_or_create(
        'product.category',
        [('name', '=', name), ('parent_id', '=', False)],
        {'name': name})

# ============ 3. 仓库库位 ============
wh = env.ref('stock.stock_location_stock')
loc_map = {}
for name in ['原材料库-面料', '原材料库-底材', '原材料库-辅料', '待检区', '不合格品区', '半成品库', '成品库', '包装材料库']:
    loc_map[name] = get_or_create(
        'stock.location',
        [('complete_name', '=', '%s/%s' % (wh.complete_name, name))],
        {'name': name, 'location_id': wh.id})

# ============ 4. 工作中心（车间产线） ============
wc_map = {}
wc_data = [
    ('裁断车间', '自动裁断机', 60),
    ('针车一线', '针车工位 20 个', 25),
    ('成型一线', '前帮机/中后帮机', 40),
    ('底部压合组', '压底机 3 台', 30),
    ('包装组', '包装台 4 组', 15),
]
for name, note, cost in wc_data:
    wc_map[name] = get_or_create('mrp.workcenter', [('name', '=', name)], {
        'name': name, 'note': note,
        'time_efficiency': 100, 'costs_hour': cost,
    })

# ============ 5. 工序（Odoo 20 工序必须挂在 BOM 上，此处仅定义数据） ============
op_data = [
    ('裁断', '裁断车间', 8),      # 每双约 8 分钟
    ('针车', '针车一线', 25),
    ('绷帮成型', '成型一线', 6),
    ('底部加工', '底部压合组', 5),
    ('包装', '包装组', 3),
]

# ============ 6. 产品资料 ============
def create_product(name, cat, uomid, **kw):
    storable = kw.pop('storable', True)
    consu = kw.pop('consu', False)  # consu=True 表示不管理库存（如鞋楦工装）
    vals = {
        'name': name, 'categ_id': cat.id, 'uom_id': uomid.id,
        'type': 'consu',
        'is_storable': False if consu else storable,
        'default_code': kw.pop('code', False),
        'list_price': kw.pop('sale', 0), 'standard_price': kw.pop('cost', 0),
        'purchase_ok': kw.pop('buy', True), 'sale_ok': kw.pop('sell', False),
        'tracking': kw.pop('tracking', False),
    }
    vals.update(kw)
    tmpl = get_or_create('product.template', [('name', '=', name)], vals)
    return tmpl.product_variant_id

# 材料
leather = create_product('头层牛皮-黑色', cat_map['面料'], uom_m, code='ML-LEA-001', cost=28, description='鞋面用头层牛皮，厚度1.4-1.6mm')
lining = create_product('针织内里布-黑色', cat_map['面料'], uom_m, code='ML-LIN-001', cost=6, description='鞋腔内里，透气针织布')
outsole = create_product('橡胶大底-男休闲款', cat_map['底材'], uom_unit, code='ML-OSO-001', cost=12, description='耐磨橡胶注塑大底')
midsole = create_product('EVA中底-男休闲款', cat_map['底材'], uom_unit, code='ML-MSO-001', cost=5)
insole = create_product('乳胶鞋垫-男款', cat_map['辅料'], uom_unit, code='ML-INS-001', cost=3)
last = create_product('鞋楦-男休闲42码', cat_map['辅料'], uom_pair, code='ML-LST-042', cost=85, consu=True, description='工装鞋楦，可循环使用', buy=True)
glue = create_product('环保水性胶水', cat_map['辅料'], uom_kg, code='ML-GLU-001', cost=35)
thread = create_product('涤纶缝纫线-黑', cat_map['辅料'], uom_unit, code='ML-THR-001', cost=2)
lace = create_product('圆头鞋带-黑-120cm', cat_map['辅料'], uom_unit, code='ML-LAC-001', cost=0.5)
shoebox = create_product('鞋盒-男休闲款', cat_map['包装材料'], uom_unit, code='PK-BOX-001', cost=2.5)
carton = create_product('外箱-双层瓦楞', cat_map['包装材料'], uom_unit, code='PK-CTN-001', cost=4)
# 成品（批次追溯）
shoe = create_product('男士休闲皮鞋-黑-42码', cat_map['成品鞋'], uom_pair,
                      code='FG-SHO-042', sale=399, cost=98, sell=True, buy=False, tracking='lot')
shoe_tmpl = shoe.product_tmpl_id

# ============ 7. 物料清单 BOM（含工序） ============
bom = env['mrp.bom'].search([('product_tmpl_id', '=', shoe_tmpl.id)], limit=1)
if not bom:
    bom_lines = [
        (leather.product_tmpl_id, 0.55), (lining.product_tmpl_id, 0.35),
        (outsole.product_tmpl_id, 2), (midsole.product_tmpl_id, 2),
        (insole.product_tmpl_id, 2), (last.product_tmpl_id, 1),
        (glue.product_tmpl_id, 0.08), (thread.product_tmpl_id, 1),
        (lace.product_tmpl_id, 2), (shoebox.product_tmpl_id, 1),
    ]
    bom = env['mrp.bom'].create({
        'product_tmpl_id': shoe_tmpl.id,
        'product_qty': 1, 'uom_id': uom_pair.id,
        'type': 'normal', 'code': 'BOM-SHO-042',
        'bom_line_ids': [(0, 0, {
            'product_id': p.id, 'product_qty': q,
        }) for p, q in bom_lines],
        'operation_ids': [(0, 0, {
            'name': op_name,
            'workcenter_id': wc_map[wc_name].id,
            'time_cycle_manual': minutes,
            'time_mode': 'manual',
            'sequence': seq,
        }) for seq, (op_name, wc_name, minutes) in enumerate(op_data, start=10)],
    })

# ============ 8. 往来单位 ============
get_or_create('res.partner', [('name', '=', '广州港汇贸易有限公司')], {
    'name': '广州港汇贸易有限公司', 'is_company': True,
    'street': '广州市荔湾区', 'phone': '020-88886666', 'email': 'purchase@ganghui.com'})
get_or_create('res.partner', [('name', '=', '温州宏达皮革有限公司')], {
    'name': '温州宏达皮革有限公司', 'is_company': True,
    'street': '温州市鹿城区', 'phone': '0577-88665544', 'email': 'sales@hongda-leather.com'})
get_or_create('res.partner', [('name', '=', '晋江华利鞋材有限公司')], {
    'name': '晋江华利鞋材有限公司', 'is_company': True,
    'street': '晋江市陈埭镇', 'phone': '0595-85123456', 'email': 'sales@huali-xc.com'})

# ============ 9. 部门 ============
for name in ['总经办', '研发部', '生产部', '品质部', '仓储部', '采购部', '销售部', '财务部']:
    get_or_create('hr.department', [('name', '=', name), ('parent_id', '=', False)], {'name': name})

# ============ 10. 启用批次管理 + 工单（工艺路线） ============
admin_user = env.ref('base.user_admin')
for group_xmlid in ['stock.group_production_lot', 'mrp.group_mrp_routings']:
    grp = env.ref(group_xmlid)
    if grp not in admin_user.all_group_ids:
        admin_user.write({'group_ids': [(4, grp.id)]})

# ============ 11. 禁用新手引导弹窗（HTTP 环境下会报错） ============
env['ir.config_parameter'].set_bool('web_tour.disable', True)

# ============ 12. 全厂公告频道 ============
if not env['discuss.channel'].search([('name', '=', '全厂公告')], limit=1):
    env['discuss.channel'].create({
        'name': '全厂公告',
        'description': '厂务通知、生产安排、质量通报（全员可见）',
        'channel_type': 'channel',
        'group_public_id': env.ref('base.group_user').id,
    })

# ============ 12. 示例：来料检验单 ============
if not env['qc.inspection'].search([], limit=1):
    insp = env['qc.inspection'].create({
        'inspection_type': 'iqc',
        'product_id': leather.id,
        'qty': 500,
        'partner_id': env['res.partner'].search([('name', '=', '温州宏达皮革有限公司')], limit=1).id,
    })
    # 触发默认检验项生成
    insp._onchange_inspection_type()

env.cr.commit()
print('SETUP_DONE')
print('成品: %s (BOM %s, %d 道工序)' % (shoe.name, bom.code, len(bom.operation_ids)))
