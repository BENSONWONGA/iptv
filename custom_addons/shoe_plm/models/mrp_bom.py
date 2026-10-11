from odoo import fields, models


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    eco_ids = fields.One2many('plm.eco', 'bom_id', string='工程变更单')
    eco_count = fields.Integer(string='变更次数', compute='_compute_eco_count')

    def _compute_eco_count(self):
        for bom in self:
            bom.eco_count = len(bom.eco_ids)

    def action_view_ecos(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': '工程变更单',
            'res_model': 'plm.eco',
            'view_mode': 'list,form',
            'domain': [('bom_id', '=', self.id)],
        }
