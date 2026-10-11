from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PlmEco(models.Model):
    _name = 'plm.eco'
    _description = '工程变更单'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(string='单号', default='新建', copy=False, readonly=True, tracking=True)
    subject = fields.Char(string='变更主题', required=True, tracking=True)
    eco_type = fields.Selection(
        [('design', '设计变更'), ('process', '工艺变更'), ('material', '材料替代'),
         ('drawing', '图纸纠错')],
        string='变更类型', required=True, default='design', tracking=True)
    state = fields.Selection(
        [('draft', '草稿'), ('review', '评审中'), ('approved', '已批准'),
         ('applied', '已执行'), ('cancelled', '已取消')],
        string='状态', default='draft', copy=False, tracking=True)
    product_tmpl_id = fields.Many2one(
        'product.template', string='产品', required=True, tracking=True)
    bom_id = fields.Many2one(
        'mrp.bom', string='当前版本BOM',
        domain="[('product_tmpl_id', '=', product_tmpl_id)]")
    new_bom_id = fields.Many2one(
        'mrp.bom', string='新版本BOM', readonly=True, copy=False)
    requested_by = fields.Many2one(
        'res.users', string='申请人', default=lambda self: self.env.user, tracking=True)
    date = fields.Date(string='申请日期', default=fields.Date.context_today, required=True)
    expected_date = fields.Date(string='预计生效日期')
    approved_by = fields.Many2one('res.users', string='批准人', readonly=True, copy=False)
    date_approved = fields.Date(string='批准日期', readonly=True, copy=False)
    applied_date = fields.Date(string='执行日期', readonly=True, copy=False)
    reason = fields.Text(string='变更原因', required=True)
    description = fields.Html(string='变更内容说明')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'plm_eco_attachment_rel', 'eco_id', 'attachment_id',
        string='技术资料/图纸')

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            bom = self.env['mrp.bom'].search(
                [('product_tmpl_id', '=', self.product_tmpl_id.id), ('active', '=', True)],
                limit=1)
            self.bom_id = bom

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '新建':
                vals['name'] = self.env['ir.sequence'].next_by_code('plm.eco') or '新建'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('只有草稿状态的变更单才能提交评审。'))
        self.write({'state': 'review'})

    def action_approve(self):
        for rec in self:
            if rec.state != 'review':
                raise UserError(_('只有评审中状态的变更单才能批准。'))
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'date_approved': fields.Date.context_today(self),
        })

    def action_apply(self):
        """执行变更：克隆新版本 BOM，归档旧版本"""
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('只有已批准的变更单才能执行。'))
            if rec.bom_id and rec.bom_id.active:
                new_bom = rec.bom_id.copy()
                rec.bom_id.active = False
                rec.write({'new_bom_id': new_bom.id})
            rec.write({
                'state': 'applied',
                'applied_date': fields.Date.context_today(self),
            })

    def action_cancel(self):
        for rec in self:
            if rec.state == 'applied':
                raise UserError(_('已执行的变更单不能取消，请新建变更单回退。'))
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_view_new_bom(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '新版本BOM',
            'res_model': 'mrp.bom',
            'view_mode': 'form',
            'res_id': self.new_bom_id.id,
        }
