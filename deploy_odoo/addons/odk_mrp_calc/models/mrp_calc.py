# -*- coding: utf-8 -*-
# 奥登科·物料需求运算（独立 MRP，对齐旧系统 P11「物料需求计算」）
# 逻辑：BOM 每双用量 × 订单数量 = 需求 → 扣可用库存 / 在途 / 已订 = 采购欠量
#       → 建议量（含损耗% / 采购比）→ 勾选欠料行一键转采购询价单
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OdkMrpCalc(models.Model):
    _name = 'odk.mrp.calc'
    _description = '物料需求运算单'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char('单号', default=lambda self: _('New'), copy=False, readonly=True)
    state = fields.Selection([('draft', '草稿'), ('done', '已运算')], string='状态',
                             default='draft', copy=False)
    product_id = fields.Many2one('product.product', string='款号（成品）', required=True)
    product_tmpl_id = fields.Many2one('product.template',
                                      related='product_id.product_tmpl_id',
                                      string='产品模板', store=True)
    product_qty = fields.Float('订单数量', required=True, default=300.0,
                               digits='Product Unit')
    uom_id = fields.Many2one(related='product_id.uom_id', string='单位')
    bom_id = fields.Many2one('mrp.bom', string='量产 BOM',
                             compute='_compute_bom_id', store=True, readonly=False)
    date_run = fields.Datetime('最后运算时间', readonly=True, copy=False)
    line_ids = fields.One2many('odk.mrp.calc.line', 'calc_id', string='材料需求明细',
                               copy=False)
    shortage_line_ids = fields.Many2many('odk.mrp.calc.line', string='欠料明细',
                                         compute='_compute_shortage_data')
    shortage_count = fields.Integer('欠料行数', compute='_compute_shortage_data')
    purchase_order_ids = fields.Many2many('purchase.order', 'odk_mrp_calc_purchase_rel',
                                          'calc_id', 'order_id', string='已转采购单',
                                          copy=False)
    purchase_count = fields.Integer('已转采购单数', compute='_compute_purchase_count')
    note = fields.Text('备注')
    company_id = fields.Many2one('res.company', string='公司',
                                 default=lambda self: self.env.company, required=True)

    @api.depends('product_id')
    def _compute_bom_id(self):
        for rec in self:
            rec.bom_id = False
            if not rec.product_id:
                continue
            # 先找款号变体级 BOM，再回落模板级（等价 mrp._bom_find 的语义）
            rec.bom_id = self.env['mrp.bom'].search([
                '|',
                ('product_id', '=', rec.product_id.id),
                '&', ('product_id', '=', False),
                     ('product_tmpl_id', '=', rec.product_tmpl_id.id),
            ], order='sequence, id', limit=1)

    @api.depends('line_ids.shortage_qty')
    def _compute_shortage_data(self):
        for rec in self:
            shorts = rec.line_ids.filtered(lambda l: l.shortage_qty > 0.0001)
            rec.shortage_line_ids = shorts
            rec.shortage_count = len(shorts)

    @api.depends('purchase_order_ids')
    def _compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.purchase_order_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('odk.mrp.calc') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # 核心动作：物料需求计算
    # ------------------------------------------------------------------
    def action_calculate(self):
        self.ensure_one()
        if not self.bom_id:
            raise UserError(_('未找到款号对应的量产 BOM，请先在「制造 → 产品 → 物料清单」维护。'))
        if self.product_qty <= 0:
            raise UserError(_('订单数量必须大于 0。'))
        factor = self.product_qty / (self.bom_id.product_qty or 1.0)

        # 采购数据汇总：已订未交 / 未确认询价 / 已入库
        products = self.bom_id.bom_line_ids.product_id
        po_map = {}
        pols = self.env['purchase.order.line'].sudo().search([
            ('product_id', 'in', products.ids),
            ('order_id.state', 'in', ('draft', 'sent', 'purchase')),
        ])
        for pol in pols:
            d = po_map.setdefault(pol.product_id.id,
                                  {'ordered': 0.0, 'unconfirmed': 0.0, 'received': 0.0})
            if pol.order_id.state == 'purchase':
                d['ordered'] += pol.product_qty - pol.qty_received
                d['received'] += pol.qty_received
            else:
                d['unconfirmed'] += pol.product_qty

        SupplierInfo = self.env['product.supplierinfo'].sudo()
        old_by_product = {l.product_id: l for l in self.line_ids}
        lines = []
        for bl in self.bom_id.bom_line_ids:
            product = bl.product_id
            d = po_map.get(product.id, {'ordered': 0.0, 'unconfirmed': 0.0, 'received': 0.0})
            seller = SupplierInfo.search(
                [('product_tmpl_id', '=', product.product_tmpl_id.id)],
                order='price', limit=1)
            old = old_by_product.get(product)
            qty_available = product.qty_available
            free_qty = product.free_qty
            lines.append((0, 0, {
                'supplier_id': seller.partner_id.id if seller else False,
                'product_id': product.id,
                'uom_id': (bl.uom_id or product.uom_id).id,
                'per_unit_qty': bl.product_qty,
                'required_qty': bl.product_qty * factor,
                'loss_pct': old.loss_pct if old else 3.0,
                'purchase_ratio': old.purchase_ratio if old else 1.0,
                'ordered_qty': d['ordered'],
                'unconfirmed_qty': d['unconfirmed'],
                'received_qty': d['received'],
                'stock_qty': qty_available,
                'free_qty': free_qty,
                'occupied_qty': qty_available - free_qty,
                'incoming_qty': product.incoming_qty,
            }))
        self.write({
            'line_ids': [(5, 0, 0)] + lines,
            'date_run': fields.Datetime.now(),
            'state': 'done',
        })
        message = '共 %d 行材料需求，其中欠料 %d 行（已标红，勾选后可转采购单）' % (
            len(lines), self.shortage_count)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'type': 'success', 'title': _('物料需求计算完成'),
                       'message': message, 'sticky': False},
        }

    # ------------------------------------------------------------------
    # 欠料转采购询价单
    # ------------------------------------------------------------------
    def action_to_purchase(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda l: l.select and l.suggested_qty > 0)
        if not lines:
            lines = self.line_ids.filtered(lambda l: l.suggested_qty > 0)
        if not lines:
            raise UserError(_('没有可转采购的欠料行（建议量 > 0）。'))
        for l in lines:
            if not l.supplier_id:
                raise UserError(_('材料 %s 未维护厂商报价，无法转采购单。')
                                % l.product_id.display_name)
        by_supplier = {}
        for l in lines:
            by_supplier.setdefault(l.supplier_id, self.env['odk.mrp.calc.line'])
            by_supplier[l.supplier_id] |= l
        orders = self.env['purchase.order']
        for supplier, group in by_supplier.items():
            orders |= self.env['purchase.order'].create({
                'partner_id': supplier.id,
                'origin': self.name,
                'order_line': [(0, 0, {
                    'product_id': l.product_id.id,
                    'product_qty': l.suggested_qty,
                    'price_unit': l._get_supplier_price(),
                }) for l in group],
            })
        self.purchase_order_ids = [(4, o.id) for o in orders]
        return {
            'type': 'ir.actions.act_window',
            'name': _('已生成的采购询价单'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', orders.ids)],
        }

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('已转采购单'),
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.purchase_order_ids.ids)],
        }


class OdkMrpCalcLine(models.Model):
    _name = 'odk.mrp.calc.line'
    _description = '物料需求运算行'
    _order = 'calc_id desc, id'

    calc_id = fields.Many2one('odk.mrp.calc', string='运算单', required=True,
                              ondelete='cascade', index=True)
    select = fields.Boolean('选择', default=False)
    supplier_id = fields.Many2one('res.partner', string='厂商名称')
    product_id = fields.Many2one('product.product', string='材料', required=True)
    default_code = fields.Char(related='product_id.default_code', string='材料编号',
                               store=True)
    categ_id = fields.Many2one('product.category',
                               related='product_id.categ_id', string='材料分类',
                               store=True)
    uom_id = fields.Many2one('uom.uom', string='单位')
    per_unit_qty = fields.Float('每双用量', digits='Product Unit')
    required_qty = fields.Float('需求数量', digits='Product Unit')
    loss_pct = fields.Float('损耗%', default=3.0)
    purchase_ratio = fields.Float('采购比', default=1.0)
    shortage_qty = fields.Float('采购欠量', digits='Product Unit',
                                compute='_compute_shortage_qty', store=True)
    suggested_qty = fields.Float('建议量', digits='Product Unit',
                                 compute='_compute_suggested_qty', store=True,
                                 readonly=False)
    ordered_qty = fields.Float('已订量', digits='Product Unit')
    unconfirmed_qty = fields.Float('未确认', digits='Product Unit')
    received_qty = fields.Float('采购入库', digits='Product Unit')
    stock_qty = fields.Float('实际库存', digits='Product Unit')
    free_qty = fields.Float('可用库存', digits='Product Unit')
    occupied_qty = fields.Float('占用库存', digits='Product Unit')
    incoming_qty = fields.Float('在途量', digits='Product Unit')

    @api.depends('required_qty', 'free_qty', 'incoming_qty', 'ordered_qty')
    def _compute_shortage_qty(self):
        for l in self:
            l.shortage_qty = l.required_qty - l.free_qty - l.incoming_qty - l.ordered_qty

    @api.depends('shortage_qty', 'loss_pct', 'purchase_ratio')
    def _compute_suggested_qty(self):
        for l in self:
            l.suggested_qty = round(
                max(0.0, l.shortage_qty) * (1 + (l.loss_pct or 0.0) / 100.0)
                * (l.purchase_ratio or 1.0), 2)

    def _get_supplier_price(self):
        self.ensure_one()
        SI = self.env['product.supplierinfo'].sudo()
        si = SI.search([
            ('product_tmpl_id', '=', self.product_id.product_tmpl_id.id),
            ('partner_id', '=', self.supplier_id.id)], order='price', limit=1)
        if not si:
            si = SI.search(
                [('product_tmpl_id', '=', self.product_id.product_tmpl_id.id)],
                order='price', limit=1)
        return si.price or 0.0
