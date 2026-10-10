# -*- coding: utf-8 -*-
"""奥登科·指令部件条码（H25/H27）：
1. 部件条码：按派工单批量生成（向导可设每张数量/张数），打印条码标签；
2. 条码合并（套码）：多张部件条码合并成一个套码，齐套配送/核对；
3. PDA 扫码作业页 /odk/dispatch/scan：扫描识别 → 部件入库/出库登记
   （联动仓库管理 in_part/out_part 自动过账）→ 扫码记录留痕。"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class OdkDispatchBarcode(models.Model):
    _name = 'odk.dispatch.barcode'
    _description = '奥登科·指令部件条码'
    _order = 'id desc'

    name = fields.Char('条码号', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'),
                       help="条码号即打印条码内容（Code128）")
    dispatch_id = fields.Many2one('odk.dispatch', string='派工单', required=True,
                                  index=True, check_company=True)
    product_id = fields.Many2one(related='dispatch_id.product_id', string='部件',
                                 store=True)
    qty = fields.Float('每张数量', required=True, digits='Product Unit',
                       help="该条码代表的部件数量")
    merge_ids = fields.Many2many(
        'odk.dispatch.barcode.merge', 'odk_barcode_merge_rel',
        'barcode_id', 'merge_id', string='所属套码')
    scan_log_ids = fields.One2many('odk.dispatch.scan.log', 'barcode_rec_id',
                                   string='扫码记录')
    scan_count = fields.Integer('扫码次数', compute='_compute_scan_count')
    note = fields.Text('备注')
    company_id = fields.Many2one('res.company',
                                 related='dispatch_id.company_id', store=True)

    @api.depends('scan_log_ids')
    def _compute_scan_count(self):
        for b in self:
            b.scan_count = len(b.scan_log_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'odk.dispatch.barcode') or _('New')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # PDA 扫码接口（/odk/dispatch/scan 页面调用）
    # ------------------------------------------------------------------
    @api.model
    def act_warehouses(self):
        recs = self.env['stock.warehouse'].search([])
        return [{'id': w.id, 'name': w.name, 'code': w.code} for w in recs]

    @api.model
    def act_lookup_barcode(self, code):
        """扫描识别：先按部件条码，再按套码；返回识别信息"""
        code = (code or '').strip()
        if not code:
            return {}
        bar = self.search([('name', '=', code)], limit=1)
        if bar:
            disp = self.env['odk.dispatch']
            type_sel = dict(disp._fields['dispatch_type'].selection)
            state_sel = dict(disp._fields['state'].selection)
            return {
                'kind': 'barcode',
                'barcode': bar.name,
                'dispatch': bar.dispatch_id.name,
                'dispatch_type': type_sel.get(bar.dispatch_id.dispatch_type, ''),
                'operation': bar.dispatch_id.operation or '',
                'state': state_sel.get(bar.dispatch_id.state, ''),
                'product': bar.product_id.display_name,
                'qty': bar.qty,
                'scans': bar.scan_count,
            }
        merge = self.env['odk.dispatch.barcode.merge'].search(
            [('name', '=', code)], limit=1)
        if merge:
            return {
                'kind': 'merge',
                'barcode': merge.name,
                'members': [{'barcode': m.name,
                             'dispatch': m.dispatch_id.name,
                             'product': m.product_id.display_name,
                             'qty': m.qty} for m in merge.member_ids],
            }
        return {}

    @api.model
    def act_register(self, code, action, qty, warehouse_id, note=''):
        """扫码登记：in=部件入库 out=部件出库；套码/未识别仅记录查询"""
        code = (code or '').strip()
        qty = float(qty or 0)
        action = (action or '').strip()
        Log = self.env['odk.dispatch.scan.log']
        if not code:
            raise UserError(_('请先扫描或输入条码'))
        bar = self.search([('name', '=', code)], limit=1)
        merge = False
        if not bar:
            merge = self.env['odk.dispatch.barcode.merge'].search(
                [('name', '=', code)], limit=1)
        if not bar and not merge:
            Log.create({'barcode': code, 'action': 'lookup', 'qty': qty,
                        'note': note or '未识别条码'})
            raise UserError(_('条码未识别：') + code)
        if merge:
            Log.create({'barcode': code, 'action': 'merge', 'qty': qty,
                        'dispatch_id': merge.member_ids[:1].dispatch_id.id,
                        'note': note or ('套码核对：%d 张部件条码'
                                         % len(merge.member_ids))})
            return {'kind': 'merge', 'members': len(merge.member_ids),
                    'message': _('套码核对完成，共 %d 张部件条码')
                    % len(merge.member_ids)}
        # 部件条码：入库 / 出库登记
        if action not in ('in', 'out'):
            Log.create({'barcode': code, 'action': 'lookup',
                        'barcode_rec_id': bar.id, 'qty': qty, 'note': note})
            return {'kind': 'barcode', 'action': 'lookup',
                    'message': _('已查询记录：%s（派工单 %s）')
                    % (bar.name, bar.dispatch_id.name)}
        if qty <= 0:
            raise UserError(_('数量必须大于 0'))
        wh = self.env['stock.warehouse'].browse(int(warehouse_id or 0)).exists()
        if not wh:
            raise UserError(_('请选择仓库'))
        doc_type = 'in_part' if action == 'in' else 'out_part'
        order = self.env['odk.wms.order'].create({
            'doc_type': doc_type,
            'warehouse_id': wh.id,
            'dispatch_id': bar.dispatch_id.id,
            'picker_id': self.env.uid if action == 'out' else False,
            'note': note or ('扫码%s登记：%s' % ('入库' if action == 'in' else '出库',
                                             bar.name)),
            'line_ids': [(0, 0, {
                'product_id': bar.product_id.id,
                'product_qty': qty,
            })],
        })
        order.action_confirm()
        Log.create({
            'barcode': code,
            'barcode_rec_id': bar.id,
            'action': action,
            'qty': qty,
            'dispatch_id': bar.dispatch_id.id,
            'wms_order_id': order.id,
            'note': note or '',
        })
        return {'kind': 'barcode', 'action': action,
                'wms': order.name,
                'message': _('部件%s已过账：%s ×%g')
                % ('入库' if action == 'in' else '出库',
                   bar.product_id.display_name, qty)}


class OdkDispatchBarcodeMerge(models.Model):
    _name = 'odk.dispatch.barcode.merge'
    _description = '奥登科·指令部件条码合并（套码）'
    _order = 'id desc'

    name = fields.Char('套码号', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'),
                       help="套码号即打印条码内容（Code128），代表一套部件")
    member_ids = fields.Many2many(
        'odk.dispatch.barcode', 'odk_barcode_merge_rel',
        'merge_id', 'barcode_id', string='成员部件条码')
    member_count = fields.Integer('成员条码数', compute='_compute_member_count')
    note = fields.Text('备注')

    @api.depends('member_ids')
    def _compute_member_count(self):
        for m in self:
            m.member_count = len(m.member_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'odk.dispatch.barcode.merge') or _('New')
        return super().create(vals_list)

    def action_view_members(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('成员部件条码'),
            'res_model': 'odk.dispatch.barcode',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.member_ids.ids)],
        }


class OdkDispatchScanLog(models.Model):
    _name = 'odk.dispatch.scan.log'
    _description = '奥登科·指令部件扫码记录'
    _order = 'id desc'

    barcode = fields.Char('扫描条码', required=True)
    barcode_rec_id = fields.Many2one('odk.dispatch.barcode', string='部件条码',
                                      index=True)
    action = fields.Selection([
        ('lookup', '查询'),
        ('in', '部件入库'),
        ('out', '部件出库'),
        ('merge', '套码核对'),
    ], string='动作', default='lookup')
    qty = fields.Float('数量', digits='Product Unit')
    dispatch_id = fields.Many2one('odk.dispatch', string='派工单', index=True)
    product_id = fields.Many2one(related='dispatch_id.product_id',
                                 string='部件', store=True)
    wms_order_id = fields.Many2one('odk.wms.order', string='关联仓库单据',
                                   readonly=True)
    user_id = fields.Many2one('res.users', string='操作员',
                              default=lambda self: self.env.user)
    date = fields.Datetime('时间', default=fields.Datetime.now)
    note = fields.Char('说明')


class OdkDispatchBarcodeWizard(models.TransientModel):
    _name = 'odk.dispatch.barcode.wizard'
    _description = '奥登科·生成部件条码向导'

    dispatch_id = fields.Many2one('odk.dispatch', string='派工单', required=True)
    label_qty = fields.Float('每张条码数量', required=True, default=1.0,
                             digits='Product Unit')
    label_count = fields.Integer('生成张数', required=True, default=10)

    @api.onchange('dispatch_id')
    def _onchange_dispatch(self):
        if self.dispatch_id:
            self.label_qty = 1.0
            self.label_count = max(1, int(self.dispatch_id.qty))

    def action_generate(self):
        self.ensure_one()
        if self.label_qty <= 0 or self.label_count <= 0:
            raise UserError(_('每张数量与张数必须大于 0'))
        if self.label_count > 500:
            raise UserError(_('单次最多生成 500 张，请分批生成'))
        Barcode = self.env['odk.dispatch.barcode']
        for _i in range(self.label_count):
            Barcode.create({
                'dispatch_id': self.dispatch_id.id,
                'qty': self.label_qty,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('指令部件条码'),
            'res_model': 'odk.dispatch.barcode',
            'view_mode': 'list,form',
            'domain': [('dispatch_id', '=', self.dispatch_id.id)],
            'context': {'default_dispatch_id': self.dispatch_id.id},
        }


class OdkDispatch(models.Model):
    _inherit = 'odk.dispatch'

    barcode_count = fields.Integer('部件条码数',
                                   compute='_compute_barcode_count')

    @api.depends('barcode_ids')
    def _compute_barcode_count(self):
        Barcode = self.env['odk.dispatch.barcode']
        for d in self:
            d.barcode_count = Barcode.search_count(
                [('dispatch_id', '=', d.id)])

    barcode_ids = fields.One2many('odk.dispatch.barcode', 'dispatch_id',
                                  string='部件条码')

    def action_open_barcode_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('生成部件条码'),
            'res_model': 'odk.dispatch.barcode.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_dispatch_id': self.id},
        }

    def action_view_barcodes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('指令部件条码'),
            'res_model': 'odk.dispatch.barcode',
            'view_mode': 'list,form',
            'domain': [('dispatch_id', '=', self.id)],
        }
