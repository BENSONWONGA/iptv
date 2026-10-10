# -*- coding: utf-8 -*-
"""奥登科·仓库管理：对齐旧系统「材料库存管理」单据体系
统一仓库业务单（15 类出入库/调拨）→ 确认即自动过账库存移动；
盘点调整单 → 一键应用库存盘点；联动 IQC（暂收待检）与采购单。"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError

# 单据类型 → 库存方向
DOC_DIRECTION = {
    'in_purchase': 'in', 'in_customer': 'in', 'in_general': 'in',
    'in_mfg_return': 'in', 'in_general_return': 'in',
    'out_mfg': 'out', 'out_supplement': 'out', 'out_trial': 'out',
    'out_general': 'out', 'out_order': 'out', 'out_purchase_return': 'out',
    'out_customer_return': 'out', 'out_resale': 'out', 'out_divert': 'out',
    'transfer': 'transfer',
}


class OdkWmsOrder(models.Model):
    _name = 'odk.wms.order'
    _description = '奥登科·仓库业务单'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单号', default=lambda self: _('New'), required=True,
                       copy=False, readonly=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirmed', '已过账'),
        ('cancel', '已取消'),
    ], string='状态', default='draft', copy=False, tracking=True)
    doc_type = fields.Selection([
        ('in_purchase', '采购入库单'),
        ('in_customer', '客供料入库'),
        ('in_general', '综合入库单'),
        ('in_mfg_return', '生产退料入库'),
        ('in_general_return', '综合退料入库'),
        ('out_mfg', '加工领料单'),
        ('out_supplement', '补料领料单'),
        ('out_trial', '试做领料单'),
        ('out_general', '综合领用单'),
        ('out_order', '指令领料单'),
        ('out_purchase_return', '采购退货单'),
        ('out_customer_return', '客供料退货'),
        ('out_resale', '材料转卖单'),
        ('out_divert', '指令材料挪用单'),
        ('transfer', '物料转仓调拨单'),
    ], string='单据类型', required=True, default='in_purchase', copy=False,
        tracking=True)
    direction = fields.Selection([
        ('in', '入库'), ('out', '出库'), ('transfer', '调拨')],
        string='库存方向', compute='_compute_direction', store=True)
    partner_id = fields.Many2one(
        'res.partner', string='供应商/客户',
        help="采购入库/采购退货填供应商；客供料入库/退货、材料转卖填客户")
    mo_id = fields.Many2one(
        'mrp.production', string='生产订单', check_company=True,
        help="领料/退料类单据可关联生产订单，便于成本追溯")
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='仓库', required=True, check_company=True)
    dest_warehouse_id = fields.Many2one(
        'stock.warehouse', string='调入仓库', check_company=True,
        help="物料转仓调拨单的目标仓库")
    date_order = fields.Datetime('单据日期', default=fields.Datetime.now)
    date_done = fields.Datetime('过账时间', copy=False, readonly=True)
    line_ids = fields.One2many('odk.wms.order.line', 'order_id', string='物料明细',
                               copy=True)
    line_count = fields.Integer('行数', compute='_compute_line_count')
    picking_id = fields.Many2one('stock.picking', string='库存单据',
                                 copy=False, readonly=True)
    note = fields.Text('备注')
    company_id = fields.Many2one('res.company', string='公司', required=True,
                                 default=lambda self: self.env.company)

    @api.depends('doc_type')
    def _compute_direction(self):
        for order in self:
            order.direction = DOC_DIRECTION.get(order.doc_type, 'in')

    @api.depends('line_ids')
    def _compute_line_count(self):
        for order in self:
            order.line_count = len(order.line_ids)

    @api.onchange('doc_type')
    def _onchange_doc_type(self):
        """切换单据类型时清空不适用的关联"""
        if self.doc_type != 'transfer':
            self.dest_warehouse_id = False
        if self.doc_type not in ('out_mfg', 'out_supplement', 'out_trial',
                                 'out_order', 'out_divert', 'in_mfg_return'):
            self.mo_id = False

    # ------------------------------------------------------------------
    # 库位解析
    # ------------------------------------------------------------------
    def _loc(self, xmlid, usage):
        loc = self.env.ref(xmlid, raise_if_not_found=False)
        if not loc:
            loc = self.env['stock.location'].search([
                ('usage', '=', usage),
                '|', ('company_id', '=', False),
                     ('company_id', '=', self.env.company.id),
            ], limit=1)
        if not loc:
            raise UserError(_('系统缺少 %s 类型的虚拟库位') % usage)
        return loc

    def _resolve_flow(self):
        """按单据类型解析 (picking_code, 源库位, 目标库位)"""
        self.ensure_one()
        stock = self.warehouse_id.lot_stock_id
        suppliers = self._loc('stock.stock_location_suppliers', 'supplier')
        customers = self._loc('stock.stock_location_customers', 'customer')
        production = self._loc('stock.location_production', 'production')
        inventory = self._loc('stock.location_inventory', 'inventory')
        # 供应商专属库位优先（如客供/委外有独立虚拟库位）
        if self.partner_id and self.partner_id.property_stock_supplier:
            suppliers = self.partner_id.property_stock_supplier
        if self.partner_id and self.partner_id.property_stock_customer:
            customers = self.partner_id.property_stock_customer
        flows = {
            'in_purchase': ('incoming', suppliers, stock),
            'in_customer': ('incoming', customers, stock),
            'in_general': ('incoming', inventory, stock),
            'in_mfg_return': ('incoming', production, stock),
            'in_general_return': ('incoming', inventory, stock),
            'out_mfg': ('outgoing', stock, production),
            'out_supplement': ('outgoing', stock, production),
            'out_trial': ('outgoing', stock, production),
            'out_general': ('outgoing', stock, production),
            'out_order': ('outgoing', stock, production),
            'out_divert': ('outgoing', stock, production),
            'out_purchase_return': ('outgoing', stock, suppliers),
            'out_customer_return': ('outgoing', stock, customers),
            'out_resale': ('outgoing', stock, customers),
        }
        return flows.get(self.doc_type, ('incoming', suppliers, stock))

    # ------------------------------------------------------------------
    # 过账（沿用委外模块验证过的库存单生成方式）
    # ------------------------------------------------------------------
    def _make_picking(self, picking_code, location_src, location_dest, moves):
        """生成并过账一张库存单据"""
        self.ensure_one()
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', picking_code),
            ('warehouse_id', '=', self.warehouse_id.id),
        ], limit=1)
        if not picking_type:
            raise UserError(_('仓库 %s 缺少 %s 类型的单据类型')
                            % (self.warehouse_id.name, picking_code))
        move_vals = [(0, 0, {
            'description_picking': line.product_id.display_name,
            'product_id': line.product_id.id,
            'product_uom_qty': line.product_qty,
            'uom_id': line.product_id.uom_id.id,
            'location_id': location_src.id,
            'location_dest_id': location_dest.id,
        }) for line in moves]
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': location_src.id,
            'location_dest_id': location_dest.id,
            'partner_id': self.partner_id.id,
            'origin': '%s %s' % (self._description, self.name),
            'move_ids': move_vals,
        })
        picking.action_confirm()
        for move in picking.move_ids:
            move.write({'quantity': move.product_uom_qty, 'picked': True})
        picking.with_context(skip_backorder=True, cancel_backorder=True).button_validate()
        picking.invalidate_recordset()
        if picking.state != 'done':
            raise UserError(_('库存单据 %s 过账未成功，当前状态 %s')
                            % (picking.name, picking.state))
        return picking

    def action_confirm(self):
        """确认过账：按单据类型自动生成并过账库存移动"""
        for order in self:
            if order.state != 'draft':
                raise UserError(_('只有草稿状态的单据才能确认过账：%s') % order.name)
            if not order.line_ids:
                raise UserError(_('物料明细为空：%s') % order.name)
            if order.doc_type == 'transfer' and not order.dest_warehouse_id:
                raise UserError(_('物料转仓调拨单必须选择调入仓库：%s') % order.name)
            if order.doc_type == 'transfer' and \
                    order.dest_warehouse_id == order.warehouse_id:
                raise UserError(_('调入仓库不能与调出仓库相同：%s') % order.name)
            if order.doc_type == 'transfer':
                code = 'internal'
                src = order.warehouse_id.lot_stock_id
                dst = order.dest_warehouse_id.lot_stock_id
            else:
                code, src, dst = order._resolve_flow()
            moves = order.line_ids.filtered(lambda l: l.product_id)
            if not moves:
                raise UserError(_('物料明细为空，无法过账：%s') % order.name)
            order.picking_id = order._make_picking(code, src, dst, moves)
            order.date_done = fields.Datetime.now()
            order.state = 'confirmed'
        return True

    def action_cancel(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(_('已过账的单据不能直接取消（库存已变动），'
                                 '请做反向单据冲销：%s') % order.name)
            order.state = 'cancel'
        return True

    def action_draft(self):
        for order in self:
            if order.state != 'cancel':
                raise UserError(_('只有已取消的单据才能退回草稿：%s') % order.name)
            order.state = 'draft'
        return True

    def action_view_picking(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('库存单据'),
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'odk.wms.order') or _('New')
        return super().create(vals_list)

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancel'):
                raise UserError(_('已过账的仓库业务单不能删除：%s') % order.name)
        return super().unlink()


class OdkWmsOrderLine(models.Model):
    _name = 'odk.wms.order.line'
    _description = '奥登科·仓库业务单行'

    order_id = fields.Many2one('odk.wms.order', string='仓库业务单',
                               required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='物料', required=True,
                                 check_company=True)
    product_qty = fields.Float('数量', required=True, default=1.0,
                                digits='Product Unit')
    uom_id = fields.Many2one('uom.uom', string='单位',
                             related='product_id.uom_id', store=True)
    company_id = fields.Many2one(related='order_id.company_id', store=True)

    _qty_positive = models.Constraint(
        "check (product_qty > 0)",
        "数量必须大于 0",
    )


class OdkWmsInventory(models.Model):
    _name = 'odk.wms.inventory'
    _description = '奥登科·盘点调整单'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单号', default=lambda self: _('New'), required=True,
                       copy=False, readonly=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('done', '已调整'),
        ('cancel', '已取消'),
    ], string='状态', default='draft', copy=False, tracking=True)
    scan_type = fields.Selection([
        ('normal', '普通盘点'),
        ('instruction', '指令盘点'),
    ], string='盘点类型', required=True, default='normal', copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='仓库',
                                    required=True, check_company=True)
    location_id = fields.Many2one(
        'stock.location', string='盘点库位', check_company=True,
        domain="[('usage', '=', 'internal')]",
        help="留空默认使用仓库的库存库位")
    date_order = fields.Datetime('单据日期', default=fields.Datetime.now)
    date_done = fields.Datetime('调整时间', copy=False, readonly=True)
    line_ids = fields.One2many('odk.wms.inventory.line', 'inv_id', string='盘点明细',
                               copy=True)
    line_count = fields.Integer('行数', compute='_compute_line_count')
    note = fields.Text('备注')
    company_id = fields.Many2one('res.company', string='公司', required=True,
                                 default=lambda self: self.env.company)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for inv in self:
            inv.line_count = len(inv.line_ids)

    @api.onchange('warehouse_id')
    def _onchange_warehouse(self):
        if self.warehouse_id and not self.location_id:
            self.location_id = self.warehouse_id.lot_stock_id

    def _get_location(self):
        self.ensure_one()
        return self.location_id or self.warehouse_id.lot_stock_id

    def action_fill_current(self):
        """带出当前系统库存，便于对账"""
        Quant = self.env['stock.quant']
        for inv in self:
            loc = inv._get_location()
            for line in inv.line_ids:
                quant = Quant.search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', loc.id),
                ], limit=1)
                line.current_qty = quant.quantity if quant else 0.0
        return True

    def action_apply(self):
        """执行盘点调整：按盘差生成盘盈盘亏库存移动（inventory 虚拟库位 <-> 库存库位）"""
        StockMove = self.env['stock.move']
        for inv in self:
            if inv.state != 'draft':
                raise UserError(_('只有草稿状态的盘点单才能执行调整：%s') % inv.name)
            if not inv.line_ids:
                raise UserError(_('盘点明细为空：%s') % inv.name)
            loc = inv._get_location()
            loss_loc = inv._loss_location()
            for line in inv.line_ids:
                if line.counted_qty < 0:
                    raise UserError(_('盘点的实盘数量不能为负数：%s')
                                    % line.product_id.display_name)
                diff = line.counted_qty - line.current_qty
                if abs(diff) < 1e-9:
                    continue
                if diff > 0:
                    src, dst = loss_loc, loc
                else:
                    src, dst = loc, loss_loc
                move = StockMove.create({
                    'description_picking': '%s %s' % (inv.name, line.product_id.display_name),
                    'product_id': line.product_id.id,
                    'product_uom_qty': abs(diff),
                    'uom_id': line.product_id.uom_id.id,
                    'location_id': src.id,
                    'location_dest_id': dst.id,
                    'company_id': inv.company_id.id,
                })
                move._action_confirm()
                move.write({'quantity': abs(diff), 'picked': True})
                move._action_done()
            inv.date_done = fields.Datetime.now()
            inv.state = 'done'
        return True

    def _loss_location(self):
        """盘盈盘亏虚拟库位（inventory loss）"""
        self.ensure_one()
        loc = self.env.ref('stock.stock_location_inventory', raise_if_not_found=False)
        if not loc:
            loc = self.env['stock.location'].search([
                ('usage', '=', 'inventory'),
                '|', ('company_id', '=', False),
                     ('company_id', '=', self.env.company.id),
            ], limit=1)
        if not loc:
            raise UserError(_('系统缺少盘盈盘亏虚拟库位'))
        return loc

    def action_cancel(self):
        for inv in self:
            if inv.state != 'draft':
                raise UserError(_('已调整的盘点单不能取消：%s') % inv.name)
            inv.state = 'cancel'
        return True

    def action_draft(self):
        for inv in self:
            if inv.state != 'cancel':
                raise UserError(_('只有已取消的盘点单才能退回草稿：%s') % inv.name)
            inv.state = 'draft'
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'odk.wms.inventory') or _('New')
        return super().create(vals_list)

    def unlink(self):
        for inv in self:
            if inv.state not in ('draft', 'cancel'):
                raise UserError(_('已调整的盘点单不能删除：%s') % inv.name)
        return super().unlink()


class OdkWmsInventoryLine(models.Model):
    _name = 'odk.wms.inventory.line'
    _description = '奥登科·盘点调整单行'

    inv_id = fields.Many2one('odk.wms.inventory', string='盘点单',
                             required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='物料', required=True,
                                  check_company=True)
    uom_id = fields.Many2one('uom.uom', string='单位',
                              related='product_id.uom_id', store=True)
    current_qty = fields.Float('账面数量', digits='Product Unit',
                               help="点「带出当前库存」自动填充")
    counted_qty = fields.Float('实盘数量', digits='Product Unit', required=True,
                               default=0.0)
    diff_qty = fields.Float('盘差', compute='_compute_diff_qty', digits='Product Unit')

    @api.depends('current_qty', 'counted_qty')
    def _compute_diff_qty(self):
        for line in self:
            line.diff_qty = line.counted_qty - line.current_qty

    company_id = fields.Many2one(related='inv_id.company_id', store=True)
