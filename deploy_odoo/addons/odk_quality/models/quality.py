# -*- coding: utf-8 -*-
"""奥登科·质量管理：质检单 + 质量异常单"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OdkQualityCheck(models.Model):
    _name = "odk.quality.check"
    _description = "奥登科·质检单"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char("单号", default="New", required=True, copy=False)
    date_check = fields.Datetime("检验日期", default=fields.Datetime.now)
    inspector_id = fields.Many2one(
        "res.users", string="检验员", default=lambda self: self.env.user)
    product_id = fields.Many2one(
        "product.product", string="物料", required=True, check_company=True)
    picking_id = fields.Many2one(
        "stock.picking", string="关联单据", check_company=True,
        help="如该质检针对某张收货/调拨/生产单，选上便于追溯")
    product_qty = fields.Float(
        "抽检数量", required=True,
        help="本次抽检/送检的数量")
    qty_passed = fields.Float("合格数量", required=True)
    qty_failed = fields.Float("不合格数量", required=True)
    result = fields.Selection([
        ("pass", "合格"),
        ("partial", "部分合格"),
        ("fail", "不合格"),
    ], string="检验结果", compute="_compute_result", store=True)
    check_type = fields.Selection([
        ("iqc", "来料检验 IQC"),
        ("ipqc", "制程检验 IPQC"),
        ("fqc", "成品检验 FQC"),
        ("oqc", "出货检验 OQC"),
    ], string="检验类型", default="iqc", required=True)
    partner_id = fields.Many2one(
        "res.partner", string="相关供应商",
        help="来料不良时填写供货厂家；委外加工不良时填写外发厂")
    note = fields.Text("检验描述", help="检验项目、标准、不良现象描述")
    company_id = fields.Many2one("res.company", string="公司", required=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one(related="company_id.currency_id")
    alert_ids = fields.One2many("odk.quality.alert", "check_id", string="异常单")
    alert_count = fields.Integer(compute="_compute_alert_count")

    @api.depends("qty_passed", "qty_failed")
    def _compute_result(self):
        for check in self:
            if (check.qty_passed or 0) <= 0 and (check.qty_failed or 0) > 0:
                check.result = "fail"
            elif (check.qty_failed or 0) <= 0 and (check.qty_passed or 0) > 0:
                check.result = "pass"
            else:
                check.result = "partial"

    @api.depends("alert_ids")
    def _compute_alert_count(self):
        for check in self:
            check.alert_count = len(check.alert_ids)

    @api.constrains("product_qty", "qty_passed", "qty_failed")
    def _check_qty(self):
        for check in self:
            if check.product_qty <= 0:
                raise UserError(_("抽检数量必须大于 0：%s") % check.name)
            if check.qty_passed < 0 or check.qty_failed < 0:
                raise UserError(_("合格/不合格数量不能为负数：%s") % check.name)
            if check.qty_passed + check.qty_failed > check.product_qty + 1e-6:
                raise UserError(_(
                    "合格 %s + 不合格 %s 超过抽检数量 %s，请核对：%s")
                    % (check.qty_passed, check.qty_failed, check.product_qty, check.name))

    @api.onchange("product_id", "picking_id")
    def _onchange_product(self):
        """关联单据时自动带出单据上的物料与数量"""
        if self.picking_id and self.picking_id.move_ids:
            first = self.picking_id.move_ids[0]
            self.product_id = first.product_id
            self.product_qty = first.product_uom_qty
            self.partner_id = self.picking_id.partner_id

    def action_create_alert(self):
        """对不合格情况一键生成质量异常单"""
        self.ensure_one()
        if self.qty_failed <= 0:
            raise UserError(_("该质检单没有不合格数量，无需生成异常单"))
        alert = self.env["odk.quality.alert"].create({
            "check_id": self.id,
            "product_id": self.product_id.id,
            "partner_id": self.partner_id.id,
            "qty_bad": self.qty_failed,
            "alert_type": "iqc" if self.check_type == "iqc" else
                          ("fqc" if self.check_type in ("fqc", "oqc") else "process"),
            "description": self.note or _("来自质检单 %s 的不合格记录") % self.name,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "odk.quality.alert",
            "res_id": alert.id,
            "view_mode": "form",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odk.quality.check") or "New"
        return super().create(vals_list)


class OdkQualityAlert(models.Model):
    _name = "odk.quality.alert"
    _description = "奥登科·质量异常单"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char("单号", default="New", required=True, copy=False)
    date_alert = fields.Datetime("发现日期", default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", string="负责人", default=lambda self: self.env.user)
    check_id = fields.Many2one(
        "odk.quality.check", string="来源质检单", check_company=True)
    product_id = fields.Many2one(
        "product.product", string="物料", required=True, check_company=True)
    partner_id = fields.Many2one("res.partner", string="责任供应商/厂家")
    qty_bad = fields.Float("不良数量", required=True)
    alert_type = fields.Selection([
        ("iqc", "来料不良"),
        ("process", "制程不良"),
        ("fqc", "成品不良"),
        ("complaint", "客户投诉"),
    ], string="不良类型", default="iqc", required=True)
    state = fields.Selection([
        ("open", "待处理"),
        ("in_progress", "处理中"),
        ("done", "已关闭"),
    ], string="状态", default="open", required=True, tracking=True)
    description = fields.Text("问题描述")
    solution = fields.Text("处理措施", help="退货/返工/让步接收/索赔等处理结果")
    company_id = fields.Many2one("res.company", string="公司", required=True,
                                 default=lambda self: self.env.company)

    def action_close(self):
        for alert in self:
            if not alert.solution:
                raise UserError(_("请先填写处理措施再关闭：%s") % alert.name)
            alert.state = "done"
        return True

    def action_open(self):
        for alert in self:
            alert.state = "in_progress"
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("odk.quality.alert") or "New"
        return super().create(vals_list)
