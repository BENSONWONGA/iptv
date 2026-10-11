from odoo import _, api, fields, models
from odoo.exceptions import UserError

# 鞋业标准检验项目模板（按检验类型）
DEFAULT_CHECKS = {
    'iqc': [
        ('外观检查', '无划伤、色差、污渍、伤残'),
        ('尺寸测量', '与规格书/样品一致，公差范围内'),
        ('材质确认', '材质与确认样品一致'),
        ('数量核对', '实际数量与送货单一致'),
        ('环保/检测报告', '供应商提供有效检测报告'),
    ],
    'ipqc': [
        ('首件确认', '首件经确认合格后方可批量生产'),
        ('针距/线迹检查', '针距均匀、无跳线断线、线迹整齐'),
        ('帮面成型质量', '对称平整、无起皱变形'),
        ('胶合强度', '贴合牢固、无开胶溢胶'),
        ('中底/大底贴合', '贴合到位、无偏移'),
    ],
    'fqc': [
        ('外观全检', '鞋面整洁、无胶渍划痕、色泽一致'),
        ('左右脚配对', '同双一致、配双正确'),
        ('尺码核对', '鞋内实际尺码与标识一致'),
        ('内部清洁', '鞋腔无杂物、线头清理干净'),
        ('包装及标识', '鞋盒/吊牌/标识正确清晰'),
    ],
    'oqc': [
        ('装箱数量核对', '按订单数量装箱、无错装漏装'),
        ('鞋盒/外箱标识', '品名尺码数量标识清晰正确'),
        ('抽检外观', '按 AQL 抽检标准执行'),
        ('条码扫描', '条码可扫、信息正确'),
    ],
}


class QcInspection(models.Model):
    _name = 'qc.inspection'
    _description = '质量检验单'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='单号', default='新建', copy=False, readonly=True, tracking=True)
    inspection_type = fields.Selection(
        [('iqc', '来料检验'), ('ipqc', '制程检验'), ('fqc', '成品检验'), ('oqc', '出货检验')],
        string='检验类型', required=True, default='iqc', tracking=True)
    state = fields.Selection(
        [('draft', '待检'), ('in_progress', '检验中'), ('passed', '合格'),
         ('failed', '不合格'), ('cancelled', '已取消')],
        string='状态', default='draft', copy=False, tracking=True)
    product_id = fields.Many2one('product.product', string='产品', required=True, tracking=True, index=True)
    lot_id = fields.Many2one('stock.lot', string='批次/序列号')
    qty = fields.Float(string='检验数量', digits='Product Unit of Measure', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='单位', related='product_id.uom_id')
    partner_id = fields.Many2one('res.partner', string='供应商')
    date = fields.Date(string='检验日期', default=fields.Date.context_today, required=True)
    inspector_id = fields.Many2one(
        'res.users', string='检验员', default=lambda self: self.env.user, tracking=True)
    picking_id = fields.Many2one('stock.picking', string='关联调拨单')
    production_id = fields.Many2one('mrp.production', string='关联生产单')
    workorder_id = fields.Many2one('mrp.workorder', string='关联工单')
    line_ids = fields.One2many('qc.inspection.line', 'inspection_id', string='检验项目', copy=True)
    ncr_ids = fields.One2many('qc.ncr', 'inspection_id', string='不合格品处置单')
    ncr_count = fields.Integer(string='处置单数量', compute='_compute_ncr_count')
    notes = fields.Text(string='备注')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', '检验单号必须唯一'),
    ]

    @api.depends('ncr_ids')
    def _compute_ncr_count(self):
        for rec in self:
            rec.ncr_count = len(rec.ncr_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '新建':
                vals['name'] = self.env['ir.sequence'].next_by_code('qc.inspection') or '新建'
        return super().create(vals_list)

    @api.onchange('inspection_type')
    def _onchange_inspection_type(self):
        """切换检验类型时自动填入鞋业标准检验项目"""
        if self.inspection_type and not self.line_ids:
            items = DEFAULT_CHECKS.get(self.inspection_type, [])
            self.line_ids = [(0, 0, {
                'sequence': idx * 10,
                'name': name,
                'standard': standard,
            }) for idx, (name, standard) in enumerate(items)]

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.picking_id and self.picking_id.partner_id:
            self.partner_id = self.picking_id.partner_id

    def action_start(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('只有待检状态的检验单才能开始检验。'))
        self.write({'state': 'in_progress'})

    def action_pass(self):
        for rec in self:
            if rec.state not in ('draft', 'in_progress'):
                raise UserError(_('当前状态不允许判定合格。'))
        self.write({'state': 'passed'})

    def action_fail(self):
        for rec in self:
            if rec.state not in ('draft', 'in_progress'):
                raise UserError(_('当前状态不允许判定不合格。'))
        self.write({'state': 'failed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset(self):
        self.write({'state': 'draft'})

    def action_create_ncr(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '不合格品处置单',
            'res_model': 'qc.ncr',
            'view_mode': 'form',
            'context': {
                'default_inspection_id': self.id,
                'default_product_id': self.product_id.id,
                'default_lot_id': self.lot_id.id,
                'default_qty': self.qty,
            },
        }

    def action_view_ncrs(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '不合格品处置单',
            'res_model': 'qc.ncr',
            'view_mode': 'list,form',
            'domain': [('inspection_id', '=', self.id)],
        }


class QcInspectionLine(models.Model):
    _name = 'qc.inspection.line'
    _description = '检验项目明细'
    _order = 'sequence, id'

    sequence = fields.Integer(string='序号', default=10)
    inspection_id = fields.Many2one(
        'qc.inspection', string='检验单', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='检验项目', required=True)
    standard = fields.Char(string='检验标准')
    actual = fields.Char(string='实测结果')
    result = fields.Selection(
        [('pass', '合格'), ('fail', '不合格'), ('na', '不适用')],
        string='判定', default='na')
    note = fields.Char(string='备注')
