# -*- coding: utf-8 -*-
"""奥登科·委外加工：委外加工单 = BOM 自动发料 + 成品收货，两步过账联动库存"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class OdkSubcontractOrder(models.Model):
    _name = "odk.subcontract.order"
    _description = "奥登科·委外加工单"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char("单号", default="New", required=True, tracking=True, copy=False)
    state = fields.Selection([
        ("draft", "草稿"),
        ("confirmed", "已发料"),
        ("done", "已收货"),
        ("cancel", "已取消"),
    ], string="状态", default="draft", tracking=True, copy=False,
        help="草稿 → 确认发料（组件出库给委外供应商）→ 成品收货（成品入库）")

    partner_id = fields.Many2one(
        "res.partner", string="委外供应商", required=True,
        domain=[("supplier_rank", ">", 0)], tracking=True,
        help="承接外发加工的厂家，如针车厂、底厂、热切厂")
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="仓库", required=True, check_company=True,
        help="组件从该仓发出，成品收回该仓")
    date_order = fields.Datetime("下单日期", default=fields.Datetime.now)
    date_due = fields.Date("约定交期", tracking=True)
    product_id = fields.Many2one(
        "product.product", string="成品", required=True, check_company=True,
        domain=[("type", "=", "consu")], tracking=True,
        help="委外加工回来的成品或半成品")
    product_tmpl_id = fields.Many2one(
        "product.template", related="product_id.product_tmpl_id", store=True)
    product_qty = fields.Float("加工数量", required=True, default=1.0, tracking=True)
    uom_id = fields.Many2one("uom.uom", string="单位", related="product_id.uom_id", store=True)
    bom_id = fields.Many2one(
        "mrp.bom", string="BOM", check_company=True,
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
        help="按该 BOM 自动带出组件物料，发料时逐项出库")
    price_unit = fields.Float("加工单价", tracking=True, help="付给委外供应商的每单位加工费")
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    amount_total = fields.Float(
        "加工金额", compute="_compute_amount_total",
        help="加工单价 × 加工数量")
    component_ids = fields.One2many(
        "odk.subcontract.order.line", "order_id", string="组件明细", copy=True)
    component_count = fields.Integer(compute="_compute_component_count")
    picking_out_id = fields.Many2one("stock.picking", string="发料单", copy=False, readonly=True)
    picking_in_id = fields.Many2one("stock.picking", string="收货单", copy=False, readonly=True)
    note = fields.Text("备注")
    company_id = fields.Many2one(
        "res.company", related="warehouse_id.company_id", store=True, readonly=True)

    @api.depends("price_unit", "product_qty")
    def _compute_amount_total(self):
        for order in self:
            order.amount_total = float_round(
                (order.price_unit or 0.0) * (order.product_qty or 0.0), precision_digits=2)

    @api.depends("component_ids")
    def _compute_component_count(self):
        for order in self:
            order.component_count = len(order.component_ids)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        """换成品时清空 BOM 与组件，避免脏数据"""
        self.bom_id = False
        self.product_qty = 1.0
        self.component_ids = [(5, 0, 0)]

    @api.onchange("bom_id", "product_qty")
    def _onchange_bom(self):
        """选 BOM / 改数量 → 按配比自动带出组件明细"""
        vals = self._prepare_component_vals()
        if vals is not None:
            self.component_ids = vals

    def _prepare_component_vals(self):
        """按 BOM 配比 × 加工数量生成组件明细行 vals；未选 BOM 返回 None"""
        self.ensure_one()
        if not self.bom_id:
            return None
        if (self.product_qty or 0.0) <= 0:
            raise UserError(_("加工数量必须大于 0"))
        bom = self.bom_id
        factor = self.product_qty / (bom.product_qty or 1.0)
        # (5,0,0) 先清空旧组件行：One2many 赋值命令列表不会自动替换已有行，
        # 不清空会导致改数量/重选 BOM 时重复追加组件，发料时双倍扣料
        lines = [(5, 0, 0)]
        for line in bom.bom_line_ids:
            if not line.product_id:
                continue
            qty = float_round(line.product_qty * factor, precision_digits=2)
            lines.append((0, 0, {
                "product_id": line.product_id.id,
                "product_qty": qty,
                "uom_id": line.product_id.uom_id.id,
            }))
        return lines

    def action_fill_components(self):
        """服务器端按 BOM 重算组件明细（供测试、批量导入或表单按钮调用）"""
        for order in self:
            vals = order._prepare_component_vals()
            if vals is None:
                raise UserError(_("请先选择 BOM：%s") % order.name)
            order.component_ids = vals
        return True

    def _sub_loc(self):
        """委外供应商的虚拟库位（收发料的中间站）；
        未单独配置时回退到全局“供应商”虚拟库位（与采购收货惯例一致）"""
        self.ensure_one()
        loc = self.partner_id.property_stock_supplier
        if not loc:
            loc = self.env.ref("stock.stock_location_suppliers", raise_if_not_found=False)
        if not loc:
            raise UserError(_("委外供应商 %s 未配置虚拟库位，且系统缺少默认供应商库位")
                            % self.partner_id.name)
        return loc

    def _production_loc(self):
        """组件核销目标库位：公司生产虚拟库位，兜底盘盈亏库位"""
        self.ensure_one()
        company = self.warehouse_id.company_id or self.env.company
        loc = self.env["stock.location"].search([
            ("usage", "=", "production"),
            "|", ("company_id", "=", False), ("company_id", "=", company.id),
        ], limit=1)
        if not loc:
            loc = self.env["stock.location"].search([
                ("usage", "=", "inventory"),
                "|", ("company_id", "=", False), ("company_id", "=", company.id),
            ], limit=1)
        if not loc:
            raise UserError(_("找不到生产/盘亏虚拟库位，无法核销在制组件"))
        return loc

    def _make_picking(self, picking_code, location_src, location_dest, moves, label):
        """生成并过账一张库存单据（沿用扫码模块验证过的过账方式）；
        moves 内每项可用 location_src_id / location_dest_id 覆盖单据级库位"""
        self.ensure_one()
        picking_type = self.env["stock.picking.type"].search([
            ("code", "=", picking_code),
            ("warehouse_id", "=", self.warehouse_id.id),
        ], limit=1)
        if not picking_type:
            raise UserError(_("仓库 %s 缺少 %s 类型的单据类型")
                            % (self.warehouse_id.name, picking_code))
        move_vals = []
        for mv in moves:
            src = mv.get("location_src_id", location_src)
            dst = mv.get("location_dest_id", location_dest)
            move_vals.append((0, 0, {
                "description_picking": mv["product"].display_name,
                "product_id": mv["product"].id,
                "product_uom_qty": mv["qty"],
                "uom_id": mv["product"].uom_id.id,
                "location_id": src if isinstance(src, int) else src.id,
                "location_dest_id": dst if isinstance(dst, int) else dst.id,
            }))
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": location_src.id,
            "location_dest_id": location_dest.id,
            "partner_id": self.partner_id.id,
            "origin": "%s %s" % (label, self.name),
            "move_ids": move_vals,
        })
        picking.action_confirm()
        for move in picking.move_ids:
            move.write({"quantity": move.product_uom_qty, "picked": True})
        picking.with_context(skip_backorder=True, cancel_backorder=True).button_validate()
        picking.invalidate_recordset()
        if picking.state != "done":
            raise UserError(_("单据 %s 过账未成功，当前状态 %s") % (picking.name, picking.state))
        return picking

    def action_confirm(self):
        """确认发料：组件逐项出库到委外供应商虚拟库位"""
        for order in self:
            if order.state != "draft":
                raise UserError(_("只有草稿状态的委外加工单才能确认发料：%s") % order.name)
            if not order.component_ids:
                raise UserError(_("请先选择 BOM 带出组件，或手工添加组件明细：%s") % order.name)
            moves = [{"product": line.product_id, "qty": line.product_qty}
                     for line in order.component_ids if line.product_id]
            if not moves:
                raise UserError(_("组件明细为空，无法发料：%s") % order.name)
            order.picking_out_id = order._make_picking(
                "internal", order.warehouse_id.lot_stock_id, order._sub_loc(), moves, "委外发料")
            order.state = "confirmed"
        return True

    def action_receive(self):
        """成品收货：成品从委外供应商虚拟库位收回入库；
        同时把发给供应商的在制组件核销到生产虚拟库位（账实同步清零）"""
        for order in self:
            if order.state != "confirmed":
                raise UserError(_("只有已发料的委外加工单才能收货：%s") % order.name)
            moves = [{"product": order.product_id, "qty": order.product_qty}]
            for line in order.component_ids:
                if not line.product_id:
                    continue
                moves.append({
                    "product": line.product_id,
                    "qty": line.product_qty,
                    "location_dest_id": order._production_loc().id,
                })
            order.picking_in_id = order._make_picking(
                "incoming", order._sub_loc(), order.warehouse_id.lot_stock_id,
                moves, "委外收货")
            order.state = "done"
        return True

    def action_cancel(self):
        for order in self:
            if order.state not in ("draft", "confirmed"):
                raise UserError(_("已收货的委外加工单不能直接取消：%s") % order.name)
            if order.state == "confirmed" and order.picking_out_id:
                done_moves = order.picking_out_id.move_ids.filtered(lambda m: m.state == "done")
                if done_moves:
                    raise UserError(_(
                        "发料单 %s 已过账出库，需先做逆向调拨把材料收回，才能取消该单：\n%s")
                        % (order.picking_out_id.name, order.name))
            order.state = "cancel"
        return True

    def action_draft(self):
        for order in self:
            if order.state != "cancel":
                raise UserError(_("只有已取消的单据才能退回草稿：%s") % order.name)
            order.state = "draft"
        return True

    def _picking_action(self, picking):
        """跳转到指定库存单据"""
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": picking.id,
            "view_mode": "form",
        }

    def action_view_picking_out(self):
        """智能按钮：打开发料单"""
        self.ensure_one()
        return self._picking_action(self.picking_out_id)

    def action_view_picking_in(self):
        """智能按钮：打开收货单"""
        self.ensure_one()
        return self._picking_action(self.picking_in_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odk.subcontract.order") or "New"
        return super().create(vals_list)

    def unlink(self):
        for order in self:
            if order.state not in ("draft", "cancel"):
                raise UserError(_("只有草稿或已取消的委外加工单才能删除：%s") % order.name)
        return super().unlink()


class OdkSubcontractOrderLine(models.Model):
    _name = "odk.subcontract.order.line"
    _description = "奥登科·委外加工单组件行"

    order_id = fields.Many2one(
        "odk.subcontract.order", string="委外加工单", required=True, ondelete="cascade")
    product_id = fields.Many2one(
        "product.product", string="组件", required=True, check_company=True,
        domain=[("type", "=", "consu")])
    product_qty = fields.Float("应发数量", required=True, default=1.0)
    uom_id = fields.Many2one("uom.uom", string="单位", related="product_id.uom_id", store=True)
    company_id = fields.Many2one(related="order_id.company_id", store=True)

    _qty_positive = models.Constraint(
        "check (product_qty > 0)",
        "组件数量必须大于 0",
    )
