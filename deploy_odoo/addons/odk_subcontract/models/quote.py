# -*- coding: utf-8 -*-
"""奥登科·制程工艺报价：委外工序单价档案（针车/成型/热切…），
下单时关联带出供应商与单价，支持报价查询"""
from odoo import _, api, fields, models


class OdkSubcontractQuote(models.Model):
    _name = "odk.subcontract.quote"
    _description = "奥登科·制程工艺报价"
    _inherit = ["mail.thread"]
    _order = "id desc"

    name = fields.Char("报价单号", default="New", required=True, copy=False, readonly=True,
                       tracking=True)
    state = fields.Selection([
        ("draft", "草稿"),
        ("confirmed", "已确认"),
        ("cancel", "已作废"),
    ], string="状态", default="draft", tracking=True, copy=False)
    partner_id = fields.Many2one(
        "res.partner", string="委外供应商", required=True,
        domain=[("supplier_rank", ">", 0)], tracking=True,
        help="承接该工序外发加工的厂家")
    product_id = fields.Many2one(
        "product.product", string="成品/半成品",
        help="适用的成品或半成品（留空表示通用报价）")
    product_tmpl_id = fields.Many2one(
        "product.template", related="product_id.product_tmpl_id", store=True)
    process_name = fields.Char("工序/制程", required=True,
                               help="如：针车、冷粘成型、热切、电绣")
    price_unit = fields.Float("加工单价", required=True, tracking=True,
                              help="付给委外供应商的每单位加工费")
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)
    date_quote = fields.Date("报价日期", default=fields.Date.context_today)
    date_valid_to = fields.Date("有效期至",
                                help="留空表示长期有效")
    is_expired = fields.Boolean("已过期", compute="_compute_is_expired")
    order_count = fields.Integer("已下单词数", compute="_compute_order_count")
    note = fields.Text("备注")
    company_id = fields.Many2one(
        "res.company", string="公司", default=lambda self: self.env.company, required=True)

    @api.depends("date_valid_to")
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for quote in self:
            quote.is_expired = bool(quote.date_valid_to and quote.date_valid_to < today)

    def _compute_order_count(self):
        for quote in self:
            quote.order_count = self.env["odk.subcontract.order"].search_count(
                [("quote_id", "=", quote.id)])

    def action_confirm(self):
        for quote in self:
            if quote.state != "draft":
                continue
            quote.state = "confirmed"
        return True

    def action_draft(self):
        for quote in self:
            if quote.state == "cancel":
                quote.state = "draft"
        return True

    def action_cancel(self):
        for quote in self:
            if quote.state != "cancel":
                quote.state = "cancel"
        return True

    def action_view_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("已下委外单"),
            "res_model": "odk.subcontract.order",
            "view_mode": "list,form",
            "domain": [("quote_id", "=", self.id)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "odk.subcontract.quote") or "New"
        return super().create(vals_list)
