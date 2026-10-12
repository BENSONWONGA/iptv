# -*- coding: utf-8 -*-
"""鞋厂驾驶舱数据源"""
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ShoeDashboard(models.Model):
    _name = 'shoe.dashboard'
    _description = '鞋厂驾驶舱数据源'

    @api.model
    def get_dashboard_data(self):
        self = self.sudo()
        user = self.env.user
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        prev_start = month_start - relativedelta(months=1)
        next_start = month_start + relativedelta(months=1)
        try:
            target = float(self.env['ir.config_parameter'].sudo().get_str(
                'shoe_dashboard.monthly_target', '') or 600000)
        except Exception:
            target = 600000

        def money(val):
            return '¥{:,.0f}'.format(val or 0.0)

        def wan(val):
            if val >= 10000:
                return '{:.1f}万'.format(val / 10000.0)
            return '{:,.0f}'.format(val or 0.0)

        def dt_start(d):
            return datetime.combine(d, datetime.min.time())

        SaleOrder = self.env['sale.order']
        done_states = ('sale', 'done')

        # ---- 销售额 ----
        sales_month = sum(SaleOrder.search([
            ('state', 'in', done_states),
            ('date_order', '>=', dt_start(month_start)),
            ('date_order', '<', dt_start(next_start))]).mapped('amount_total'))
        sales_prev = sum(SaleOrder.search([
            ('state', 'in', done_states),
            ('date_order', '>=', dt_start(prev_start)),
            ('date_order', '<', dt_start(month_start))]).mapped('amount_total'))
        pct = None
        if sales_prev:
            pct = (sales_month - sales_prev) / sales_prev * 100.0
        progress = min(sales_month / target * 100.0, 100.0) if target else 0.0

        # ---- 欠款 ----
        try:
            amount_due = sum(self.env['account.move.line'].search([
                ('account_type', '=', 'asset_receivable'),
                ('parent_state', '=', 'posted'),
                ('reconciled', '=', False),
                ('amount_residual', '>', 0)]).mapped('amount_residual'))
        except Exception:
            amount_due = 0.0

        # ---- 数量类 ----
        quotations = SaleOrder.search_count([('state', 'in', ('draft', 'sent'))])
        my_activities = self.env['mail.activity'].search_count(
            [('user_id', '=', user.id)]) if 'mail.activity' in self.env else 0
        open_tasks = self.env['project.task'].search_count(
            [('stage_id.fold', '=', False)]) if 'project.task' in self.env else 0
        contacts = self.env['res.partner'].search_count([('active', '=', True)])
        new_contacts = self.env['res.partner'].search_count(
            [('create_date', '>=', dt_start(month_start))])
        prev_contacts = self.env['res.partner'].search_count([
            ('create_date', '>=', dt_start(prev_start)),
            ('create_date', '<', dt_start(month_start))])
        productions = self.env['mrp.production'].search_count(
            [('state', 'not in', ('done', 'cancel'))])
        qc_pending = 0
        try:
            qc_pending = self.env['x_qc_inspection'].search_count(
                [('x_state', 'in', ('draft', 'doing'))])
        except Exception:
            pass

        # ---- KPI 卡片 ----
        kpis = [
            {'id': 'sales', 'label': '本月销售额', 'value': money(sales_month),
             'sub': '本月', 'icon': 'fa-line-chart', 'color': 'green',
             'badge': ('▲ +%.0f%%' % pct) if pct is not None and pct >= 0 else ('▼ %.0f%%' % pct) if pct is not None else False,
             'badge_cls': 'up' if (pct or 0) >= 0 else 'down',
             'progress': progress,
             'progress_text': '目标 %s · %d%%' % (money(target), progress)},
            {'id': 'quotation', 'label': '待跟进报价单', 'value': str(quotations),
             'sub': '全部', 'icon': 'fa-file-text-o', 'color': 'orange'},
            {'id': 'due', 'label': '客户欠款', 'value': money(amount_due),
             'sub': '全部', 'icon': 'fa-credit-card', 'color': 'red'},
            {'id': 'production', 'label': '生产中工单', 'value': str(productions),
             'sub': '裁断/针车/成型', 'icon': 'fa-industry', 'color': 'purple'},
            {'id': 'qc', 'label': '待处理检验单', 'value': str(qc_pending),
             'sub': 'IQC/IPQC/FQC/OQC', 'icon': 'fa-check-square-o', 'color': 'teal'},
            {'id': 'activity', 'label': '我的活动', 'value': str(my_activities),
             'sub': '全部', 'icon': 'fa-clock-o', 'color': 'blue'},
            {'id': 'task', 'label': '待办任务', 'value': str(open_tasks),
             'sub': '全部', 'icon': 'fa-list-ul', 'color': 'teal'},
            {'id': 'contact', 'label': '联系人', 'value': str(contacts),
             'sub': '本月', 'icon': 'fa-users', 'color': 'green',
             'badge': ('▲ +%.0f%%' % (new_contacts / prev_contacts * 100.0)) if prev_contacts and new_contacts >= prev_contacts
                      else ('▼ %.0f%%' % ((new_contacts - prev_contacts) / prev_contacts * 100.0)) if prev_contacts else ('新增 %d' % new_contacts) if new_contacts else False,
             'badge_cls': 'up'},
        ]

        # ---- 快捷入口 ----
        def act_id(xmlid):
            try:
                rec = self.env.ref(xmlid, raise_if_not_found=False)
                return rec.id if rec else False
            except Exception:
                return False

        qc_action = self.env['ir.actions.act_window'].search(
            [('res_model', '=', 'x_qc_inspection')], limit=1)
        shortcuts = [
            {'label': '新建报价单', 'icon': 'fa-plus', 'aid': False, 'action': 'new_quotation'},
            {'label': '销售订单', 'icon': 'fa-shopping-cart', 'aid': act_id('sale.action_orders')},
            {'label': '生产工单', 'icon': 'fa-industry', 'aid': act_id('mrp.mrp_production_action')},
            {'label': '质检检验单', 'icon': 'fa-check-square-o', 'aid': qc_action.id or False},
            {'label': '采购订单', 'icon': 'fa-truck', 'aid': act_id('purchase.purchase_form_action')},
            {'label': '员工', 'icon': 'fa-id-badge', 'aid': act_id('hr.open_view_employee_list')},
        ]

        # ---- 近 6 个月销售柱状图 ----
        chart_start = month_start - relativedelta(months=5)
        rows = SaleOrder._read_group(
            [('state', 'in', done_states), ('date_order', '>=', dt_start(chart_start))],
            ['date_order:month'], ['amount_total:sum'])
        by_month = {}
        for g, agg in rows:
            key = (g.year, g.month)
            by_month[key] = by_month.get(key, 0.0) + (agg or 0.0)
        months = []
        for i in range(6):
            d = chart_start + relativedelta(months=i)
            val = by_month.get((d.year, d.month), 0.0)
            months.append({'label': '%d月' % d.month, 'value': val, 'short': wan(val)})
        chart_total = sum(m['value'] for m in months)

        # ---- 最新订单 ----
        state_map = {'sale': ('已确认', 'sale'), 'done': ('已完成', 'sale'),
                     'draft': ('草稿', 'draft'), 'sent': ('已发送', 'sent'),
                     'cancel': ('已取消', 'cancel')}
        orders = []
        for o in SaleOrder.search([], order='date_order desc', limit=6):
            st, cls = state_map.get(o.state, (o.state, 'draft'))
            orders.append({'id': o.id, 'name': o.name,
                           'date': fields.Date.context_today(self, o.date_order).strftime('%m月%d日')
                           if o.date_order else '',
                           'amount': money(o.amount_total), 'state': st, 'cls': cls})

        return {
            'user': user.name,
            'company': self.env.company.name,
            'kpis': kpis,
            'shortcuts': [sc for sc in shortcuts if sc.get('aid') or sc.get('action')],
            'months': months,
            'chart_total': money(chart_total),
            'orders': orders,
        }
