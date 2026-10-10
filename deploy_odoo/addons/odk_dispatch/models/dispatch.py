# -*- coding: utf-8 -*-
"""奥登科·现场派工：派工单（冲裁/手工/工艺）+ 派工日报（件资产量）
联动仓库管理：派工领料/补料/退料/部件出入库通过 odk.wms.order 挂派工单过账库存。"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OdkDispatch(models.Model):
    _name = 'odk.dispatch'
    _description = '奥登科·派工单'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单号', default=lambda self: _('New'), required=True,
                       copy=False, readonly=True)
    dispatch_type = fields.Selection([
        ('cutting', '冲裁派工单'),
        ('manual', '手工派工单'),
        ('process', '工艺派工单'),
    ], string='派工类型', required=True, default='cutting', copy=False,
        tracking=True)
    state = fields.Selection([
        ('draft', '草稿'),
        ('assigned', '已派工'),
        ('producing', '生产中'),
        ('done', '已完成'),
        ('cancel', '已取消'),
    ], string='状态', default='draft', copy=False, tracking=True)
    mo_id = fields.Many2one('mrp.production', string='生产订单',
                            check_company=True,
                            help="由生产订单/MRP运算下发的指令可在此关联")
    product_id = fields.Many2one('product.product', string='产品/部件',
                                 required=True, check_company=True)
    qty = fields.Float('派工数量', required=True, digits='Product Unit')
    uom_id = fields.Many2one(related='product_id.uom_id', string='单位',
                             store=True)
    qty_done = fields.Float('完工数量', compute='_compute_qty_done', store=True,
                            digits='Product Unit',
                            help="已确认日报的合格数量累计")
    operation = fields.Char('工序', help="如：冲裁、针车、成型、贴合")
    workcenter_id = fields.Many2one('mrp.workcenter', string='工作中心',
                                     check_company=True)
    user_id = fields.Many2one('res.users', string='派工负责人',
                              default=lambda self: self.env.user)
    date_start = fields.Date('计划开工')
    date_end = fields.Date('计划完工')
    date_actual = fields.Datetime('实际完工', copy=False, readonly=True)
    material_ids = fields.One2many('odk.wms.order', 'dispatch_id',
                                   string='派工领料单')
    material_count = fields.Integer('领料单数', compute='_compute_counts')
    report_ids = fields.One2many('odk.dispatch.report', 'dispatch_id',
                                string='派工日报')
    report_count = fields.Integer('日报数', compute='_compute_counts')
    note = fields.Text('备注')
    company_id = fields.Many2one('res.company', string='公司', required=True,
                                 default=lambda self: self.env.company)

    @api.depends('report_ids.state', 'report_ids.qty_produced')
    def _compute_qty_done(self):
        for d in self:
            d.qty_done = sum(r.qty_produced for r in d.report_ids
                             if r.state == 'confirmed')

    @api.depends('material_ids', 'report_ids')
    def _compute_counts(self):
        for d in self:
            d.material_count = len(d.material_ids)
            d.report_count = len(d.report_ids)

    # ------------------------------------------------------------------
    # 状态流转：草稿 → 已派工 → 生产中 → 已完成
    # ------------------------------------------------------------------
    def action_assign(self):
        for d in self:
            if d.state != 'draft':
                raise UserError(_('只有草稿状态的派工单才能派工：%s') % d.name)
            if d.qty <= 0:
                raise UserError(_('派工数量必须大于 0：%s') % d.name)
            d.state = 'assigned'
        return True

    def action_start(self):
        for d in self:
            if d.state != 'assigned':
                raise UserError(_('只有已派工的派工单才能开工：%s') % d.name)
            d.state = 'producing'
        return True

    def action_finish(self):
        for d in self:
            if d.state != 'producing':
                raise UserError(_('只有生产中的派工单才能完工：%s') % d.name)
            if d.qty_done <= 0:
                raise UserError(_('还没有确认过日报（完工数量为 0），不能完工：%s')
                                % d.name)
            d.write({'state': 'done', 'date_actual': fields.Datetime.now()})
        return True

    def action_cancel(self):
        for d in self:
            if d.state == 'done':
                raise UserError(_('已完成的派工单不能取消：%s') % d.name)
            d.state = 'cancel'
        return True

    def action_draft(self):
        for d in self:
            if d.state != 'cancel':
                raise UserError(_('只有已取消的派工单才能退回草稿：%s') % d.name)
            d.state = 'draft'
        return True

    def action_view_materials(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('派工领料单'),
            'res_model': 'odk.wms.order',
            'view_mode': 'list,form',
            'domain': [('dispatch_id', '=', self.id)],
            'context': {'default_dispatch_id': self.id,
                        'default_doc_type': 'out_mfg'},
        }

    def action_view_reports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('派工日报'),
            'res_model': 'odk.dispatch.report',
            'view_mode': 'list,form',
            'domain': [('dispatch_id', '=', self.id)],
            'context': {'default_dispatch_id': self.id},
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'odk.dispatch') or _('New')
        return super().create(vals_list)

    def unlink(self):
        for d in self:
            if d.state not in ('draft', 'cancel'):
                raise UserError(_('已派工/生产中/已完成的派工单不能删除：%s')
                                % d.name)
        return super().unlink()

    _qty_positive = models.Constraint(
        "check (qty > 0)",
        "派工数量必须大于 0",
    )


class OdkDispatchReport(models.Model):
    _name = 'odk.dispatch.report'
    _description = '奥登科·派工日报'
    _inherit = ['mail.thread']
    _order = 'id desc'

    name = fields.Char('单号', default=lambda self: _('New'), required=True,
                       copy=False, readonly=True)
    date_report = fields.Date('日报日期', required=True,
                              default=fields.Date.context_today)
    dispatch_id = fields.Many2one('odk.dispatch', string='派工单',
                                  required=True, ondelete='cascade',
                                  index=True, check_company=True)
    product_id = fields.Many2one(related='dispatch_id.product_id',
                                 string='产品/部件', store=True)
    user_id = fields.Many2one('res.users', string='操作员',
                              default=lambda self: self.env.user)
    qty_produced = fields.Float('合格数量', required=True,
                                digits='Product Unit')
    qty_scrapped = fields.Float('不合格数量', default=0.0,
                                digits='Product Unit')
    work_hours = fields.Float('工时(小时)', default=0.0)
    rate = fields.Float('件资单价', digits='Product Price', default=0.0,
                        help="计件工资单价，金额 = 合格数量 × 单价")
    amount = fields.Float('计件金额', compute='_compute_amount', store=True,
                          digits='Product Price')
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirmed', '已确认'),
        ('cancel', '已取消'),
    ], string='状态', default='draft', copy=False, tracking=True)
    note = fields.Text('备注')
    company_id = fields.Many2one('res.company', string='公司', required=True,
                                 default=lambda self: self.env.company)

    @api.depends('qty_produced', 'rate')
    def _compute_amount(self):
        for r in self:
            r.amount = r.qty_produced * r.rate

    @api.constrains('qty_produced', 'qty_scrapped')
    def _check_qty(self):
        for r in self:
            if r.qty_produced <= 0:
                raise UserError(_('合格数量必须大于 0：%s') % r.name)
            if r.qty_scrapped < 0:
                raise UserError(_('不合格数量不能为负数：%s') % r.name)

    def action_confirm(self):
        for rep in self:
            if rep.state != 'draft':
                raise UserError(_('只有草稿状态的日报才能确认：%s') % rep.name)
            rep.state = 'confirmed'
        # 完工数报满自动完工
        for rep in self:
            d = rep.dispatch_id
            if d.state == 'producing' and d.qty_done >= d.qty - 1e-9:
                d.write({'state': 'done',
                         'date_actual': fields.Datetime.now()})
        return True

    def action_cancel(self):
        for rep in self:
            if rep.state == 'confirmed':
                raise UserError(
                    _('已确认的日报不能直接取消（完工数已计入派工单），'
                      '请先联系管理员：%s') % rep.name)
            rep.state = 'cancel'
        return True

    def action_draft(self):
        for rep in self:
            if rep.state != 'cancel':
                raise UserError(_('只有已取消的日报才能退回草稿：%s') % rep.name)
            rep.state = 'draft'
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'odk.dispatch.report') or _('New')
        return super().create(vals_list)

    def unlink(self):
        for rep in self:
            if rep.state == 'confirmed':
                raise UserError(_('已确认的日报不能删除（完工数已计入派工单）：%s')
                                % rep.name)
        return super().unlink()


class OdkWmsOrder(models.Model):
    """仓库业务单扩展：挂派工单 + 领料人"""
    _inherit = 'odk.wms.order'

    dispatch_id = fields.Many2one(
        'odk.dispatch', string='派工单', index=True, check_company=True,
        help="派工领料/补料/退料/部件出入库时关联的派工单")
    picker_id = fields.Many2one(
        'res.users', string='领料人', default=lambda self: self.env.user,
        help="出库领料类单据的领料人，用于个人领料核算")
