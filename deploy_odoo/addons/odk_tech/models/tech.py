# -*- coding: utf-8 -*-
# 奥登科鞋业 · 技转管理模块（架构版）
from odoo import api, fields, models


def _next(env, code, prefix):
    try:
        seq = env['ir.sequence'].next_by_code(code)
        return seq or prefix
    except Exception:
        return prefix


class TechConfirm(models.Model):
    """D01 量产确认单：技转核心单据，冻结 BOM + 工艺 + SOP"""
    _name = 'odk.tech.confirm'
    _description = '量产确认单'
    _order = 'id desc'

    name = fields.Char('单号', required=True)
    style_id = fields.Many2one(
        'product.template', string='鞋款', required=True,
        domain="[('sale_ok', '=', True)]")
    customer_id = fields.Many2one('res.partner', string='客户')
    date_confirm = fields.Date('确认日期', default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', '草稿'),
        ('confirmed', '已确认'),
        ('frozen', '技术冻结')], string='状态', default='draft')
    bom_id = fields.Many2one('mrp.bom', string='用量BOM')
    routing_id = fields.Many2one('odk.tech.routing', string='部件工艺流程单')
    sop_id = fields.Many2one('odk.tech.sop', string='鞋款SOP')
    note = fields.Text('备注')
    change_ids = fields.One2many('odk.tech.change', 'confirm_id', string='确认变更单')
    substitute_ids = fields.One2many('odk.tech.substitute', 'confirm_id', string='材料替换单')
    trial_ids = fields.One2many('odk.tech.trial', 'confirm_id', string='试做单')
    change_count = fields.Integer('变更数', compute='_compute_counts')
    substitute_count = fields.Integer('替换数', compute='_compute_counts')
    trial_count = fields.Integer('试做数', compute='_compute_counts')

    @api.depends('change_ids', 'substitute_ids', 'trial_ids')
    def _compute_counts(self):
        for rec in self:
            rec.change_count = len(rec.change_ids)
            rec.substitute_count = len(rec.substitute_ids)
            rec.trial_count = len(rec.trial_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = _next(self.env, 'odk.tech.confirm', 'QRS')
        return super().create(vals_list)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_freeze(self):
        self.write({'state': 'frozen'})

    def action_draft(self):
        self.write({'state': 'draft'})


class TechChange(models.Model):
    """D02 确认变更单（工程变更 ECN）"""
    _name = 'odk.tech.change'
    _description = '确认变更单'
    _order = 'id desc'

    name = fields.Char('单号', required=True)
    confirm_id = fields.Many2one(
        'odk.tech.confirm', string='量产确认单', required=True)
    change_type = fields.Selection([
        ('bom', '用量变更'),
        ('material', '材料变更'),
        ('process', '工艺变更'),
        ('other', '其他')], string='变更类型', default='bom')
    reason = fields.Text('变更原因', required=True)
    content = fields.Text('变更内容')
    date_change = fields.Date('变更日期', default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', '待审批'),
        ('approved', '已审批'),
        ('applied', '已执行')], string='状态', default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = _next(self.env, 'odk.tech.change', 'ECN')
        return super().create(vals_list)

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_apply(self):
        self.write({'state': 'applied'})


class TechRouting(models.Model):
    """D09 部件工艺流程单 + D06 工序设置"""
    _name = 'odk.tech.routing'
    _description = '部件工艺流程单'
    _order = 'id desc'

    name = fields.Char('单号', required=True)
    style_id = fields.Many2one('product.template', string='鞋款')
    confirm_id = fields.Many2one('odk.tech.confirm', string='量产确认单')
    note = fields.Text('备注')
    line_ids = fields.One2many('odk.tech.routing.line', 'routing_id', string='工序明细')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = _next(self.env, 'odk.tech.routing', 'GY')
        return super().create(vals_list)


class TechRoutingLine(models.Model):
    """工艺流程行：部件 → 工序 → 工位/设备 → 工时"""
    _name = 'odk.tech.routing.line'
    _description = '部件工序行'
    _order = 'sequence, id'

    sequence = fields.Integer('序号', default=10)
    routing_id = fields.Many2one('odk.tech.routing', string='工艺流程单', required=True,
                                 ondelete='cascade')
    component = fields.Selection([
        ('cutting', '裁断'),
        ('vamp', '鞋面'),
        ('stitching', '针车'),
        ('lasting', '钳帮/成型'),
        ('outsole', '大底'),
        ('insole', '中底/内里'),
        ('assembly', '成型组装'),
        ('packing', '包装')], string='部件/环节', default='assembly')
    process = fields.Char('工序名称', required=True)
    work_center = fields.Char('工位/设备')
    cycle_time = fields.Float('单双工时(秒)')
    description = fields.Char('工艺要求')


class TechSop(models.Model):
    """D04 鞋款SOP管理"""
    _name = 'odk.tech.sop'
    _description = '鞋款SOP'
    _order = 'id desc'

    name = fields.Char('名称', required=True)
    style_id = fields.Many2one('product.template', string='鞋款')
    version = fields.Char('版本', default='V1.0')
    date_effective = fields.Date('生效日期', default=fields.Date.context_today)
    content = fields.Html('作业指导内容')
    note = fields.Text('备注')


class TechLast(models.Model):
    """楦模档案"""
    _name = 'odk.tech.last'
    _description = '楦模档案'
    _order = 'id desc'

    name = fields.Char('楦模编号', required=True)
    style_id = fields.Many2one('product.template', string='适用鞋款')
    size_range = fields.Char('尺码范围', default='40-44')
    material = fields.Char('楦模材质', default='铝楦')
    supplier_id = fields.Many2one('res.partner', string='制作厂商')
    state = fields.Selection([
        ('in_use', '使用中'),
        ('idle', '闲置'),
        ('maintenance', '维修中'),
        ('scrapped', '已报废')], string='状态', default='in_use')
    note = fields.Text('备注')


class TechSubstitute(models.Model):
    """D07 确认单材料替换"""
    _name = 'odk.tech.substitute'
    _description = '材料替换单'
    _order = 'id desc'

    name = fields.Char('单号', required=True)
    confirm_id = fields.Many2one(
        'odk.tech.confirm', string='量产确认单', required=True)
    orig_product_id = fields.Many2one('product.product', string='原材料', required=True)
    new_product_id = fields.Many2one('product.product', string='替换材料', required=True)
    qty = fields.Float('用量', default=1.0)
    reason = fields.Char('替换原因')
    date_sub = fields.Date('替换日期', default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', '待审批'),
        ('approved', '已审批')], string='状态', default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = _next(self.env, 'odk.tech.substitute', 'TR')
        return super().create(vals_list)

    def action_approve(self):
        self.write({'state': 'approved'})


class TechTrial(models.Model):
    """试做D02 量产试做单"""
    _name = 'odk.tech.trial'
    _description = '量产试做单'
    _order = 'id desc'

    name = fields.Char('单号', required=True)
    confirm_id = fields.Many2one('odk.tech.confirm', string='量产确认单')
    product_id = fields.Many2one('product.product', string='试做规格', required=True)
    product_qty = fields.Float('试做数量', default=12.0)
    uom_id = fields.Many2one('uom.uom', string='单位')
    date_planned = fields.Date('计划日期', default=fields.Date.context_today)
    result_note = fields.Text('试做结果')
    state = fields.Selection([
        ('draft', '草稿'),
        ('doing', '试做中'),
        ('done', '完成')], string='状态', default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                vals['name'] = _next(self.env, 'odk.tech.trial', 'SZ')
        return super().create(vals_list)

    def action_start(self):
        self.write({'state': 'doing'})

    def action_done(self):
        self.write({'state': 'done'})

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id


class TechProgress(models.Model):
    """D10 新款产前试做进度 / G13 AOK试做进度"""
    _name = 'odk.tech.progress'
    _description = '产前试做进度'
    _order = 'id desc'

    name = fields.Char('名称', compute='_compute_name', store=True)
    style_id = fields.Many2one('product.template', string='鞋款', required=True)
    customer_id = fields.Many2one('res.partner', string='客户')
    season = fields.Char('订单季节', default='2026春季')
    stage = fields.Selection([
        ('dev', '开发样'),
        ('trial', '产前试做'),
        ('aok', 'AOK送样'),
        ('approved', '客户确认OK'),
        ('ready', '可量产')], string='阶段', default='dev')
    date_dev = fields.Date('开发样日期')
    date_trial = fields.Date('试做日期')
    date_aok = fields.Date('AOK送样日期')
    date_approved = fields.Date('客户确认日期')
    note = fields.Text('进度备注')

    @api.depends('style_id')
    def _compute_name(self):
        for rec in self:
            rec.name = (rec.style_id.name or '') + ' 产前进度'

    def action_next_stage(self):
        order = ['dev', 'trial', 'aok', 'approved', 'ready']
        for rec in self:
            idx = order.index(rec.stage) if rec.stage in order else 0
            rec.stage = order[min(idx + 1, len(order) - 1)]
