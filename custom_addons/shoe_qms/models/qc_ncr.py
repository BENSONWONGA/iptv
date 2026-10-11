from odoo import _, api, fields, models
from odoo.exceptions import UserError


class QcNcr(models.Model):
    _name = 'qc.ncr'
    _description = '不合格品处置单'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(string='单号', default='新建', copy=False, readonly=True, tracking=True)
    inspection_id = fields.Many2one(
        'qc.inspection', string='来源检验单', index=True, tracking=True)
    product_id = fields.Many2one(
        'product.product', string='产品', required=True, tracking=True)
    lot_id = fields.Many2one('stock.lot', string='批次/序列号')
    qty = fields.Float(string='不合格数量', digits='Product Unit of Measure', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='单位', related='product_id.uom_id')
    disposition = fields.Selection(
        [('rework', '返工'), ('concession', '让步接收'), ('scrap', '报废'),
         ('return', '退货'), ('sort', '挑选使用')],
        string='处置方式', default='rework', tracking=True)
    state = fields.Selection(
        [('draft', '待处理'), ('processing', '处理中'), ('closed', '已关闭')],
        string='状态', default='draft', copy=False, tracking=True)
    root_cause = fields.Text(string='原因分析')
    corrective_action = fields.Text(string='纠正/预防措施')
    responsible_id = fields.Many2one(
        'res.users', string='责任人', default=lambda self: self.env.user)
    date = fields.Date(string='发现日期', default=fields.Date.context_today, required=True)
    date_closed = fields.Date(string='关闭日期', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '新建':
                vals['name'] = self.env['ir.sequence'].next_by_code('qc.ncr') or '新建'
        return super().create(vals_list)

    def action_process(self):
        self.write({'state': 'processing'})

    def action_close(self):
        for rec in self:
            if not rec.corrective_action:
                raise UserError(_('请先填写纠正/预防措施，再关闭处置单。'))
        self.write({'state': 'closed', 'date_closed': fields.Date.context_today(self)})

    def action_reset(self):
        self.write({'state': 'draft', 'date_closed': False})
