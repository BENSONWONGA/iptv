#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鞋业加工厂业务系统 —— 纯 RPC 部署脚本（Odoo 20）
通过 JSON-RPC 完成：标准模块安装 + QMS/PLM 动态建模 + 鞋厂主数据 + 自动化规则

用法:
    python3 deploy_rpc.py --url http://220.162.99.166:9000 --db benson \
        --user admin --password XXX [--phase all|modules|models|data|verify]
"""
import argparse
import json
import logging
import sys
import time

import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S')
_logger = logging.getLogger('deploy')

# ============================= RPC 封装 =============================

class OdooRPC:

    def __init__(self, url, db, user, password):
        self.url = url.rstrip('/')
        self.db = db
        self.user = user
        self.password = password
        self.uid = None
        self.session = requests.Session()
        self.session.headers['Content-Type'] = 'application/json'
        self.timeout = 1800  # 模块安装可能很久

    def _post(self, endpoint, payload):
        resp = self.session.post(self.url + endpoint, data=json.dumps(payload), timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if 'error' in data:
            err = data['error']
            msg = err.get('data', {}).get('message') or err.get('message', str(err))
            raise RuntimeError('RPC 错误 [%s]: %s' % (endpoint, msg))
        return data.get('result')

    def authenticate(self):
        result = self._post('/web/session/authenticate', {
            'jsonrpc': '2.0',
            'params': {'db': self.db, 'login': self.user, 'password': self.password},
        })
        if not result or not result.get('uid'):
            raise RuntimeError('登录失败：账号或密码错误')
        self.uid = result['uid']
        _logger.info('登录成功: uid=%s 用户=%s', self.uid, result.get('name'))
        return self.uid

    def call(self, model, method, args=None, kwargs=None):
        if self.uid is None:
            self.authenticate()
        return self._post('/web/dataset/call_kw', {
            'jsonrpc': '2.0',
            'params': {
                'model': model, 'method': method,
                'args': args or [], 'kwargs': kwargs or {},
            },
        })

    # ---- 便捷方法 ----
    def search(self, model, domain, limit=None, order=None):
        kw = {}
        if limit: kw['limit'] = limit
        if order: kw['order'] = order
        return self.call(model, 'search', [domain], kw)

    def search_count(self, model, domain):
        return self.call(model, 'search_count', [domain])

    def read(self, model, ids, fields=None):
        return self.call(model, 'read', [ids], {'fields': fields} if fields else {})

    def create(self, model, vals):
        return self.call(model, 'create', [vals])

    def write(self, model, ids, vals):
        return self.call(model, 'write', [ids, vals])

    def fields_get(self, model, fields=None, attrs=None):
        kw = {}
        if fields: kw['fields'] = fields
        if attrs: kw['attributes'] = attrs
        return self.call(model, 'fields_get', [], kw)

    def ref(self, xmlid):
        """返回 xmlid 对应的记录 id"""
        module, name = xmlid.split('.', 1)
        ids = self.search('ir.model.data', [('module', '=', module), ('name', '=', name)], limit=1)
        if not ids:
            return None
        return self.read('ir.model.data', ids, ['res_id'])[0]['res_id']

    def execute(self, model, method, *args, **kw):
        return self.call(model, method, list(args), kw)


# ============================= 工具函数 =============================

def get_or_create(rpc, model, domain, vals, search_order=None):
    ids = rpc.search(model, domain, limit=1, order=search_order)
    if ids:
        return ids[0], False
    return rpc.create(model, vals), True


def ensure_module_state(rpc, tech_name):
    ids = rpc.search('ir.module.module', [('name', '=', tech_name)], limit=1)
    if not ids:
        return None
    return rpc.read('ir.module.module', ids, ['state'])[0]


# ============================= Phase 1: 标准模块 =============================

# ERP + OA + WMS + MES 全覆盖（Odoo 20 社区版）
MODULES = [
    'sale_management',      # 销售
    'purchase',             # 采购
    'mrp',                  # 制造 MRP/工单/工序 (MES)
    'mrp_subcontracting',   # 外协加工
    'account',              # 财务会计 (ERP)
    'l10n_cn',              # 中国会计科目表 + 税率
    'hr_attendance',        # 考勤 (OA)
    'hr_holidays',          # 休假 (OA)
    'hr_expense',           # 费用报销 (OA)
    'hr_timesheet',         # 工时表 (OA)
    'project',              # 项目管理 (OA)
    'base_automation',      # 自动化规则引擎（QC/PLM 动态建模依赖）
]

def phase_modules(rpc):
    _logger.info('===== Phase 1: 安装标准模块 =====')
    installed, to_install = [], []
    for name in MODULES:
        mod = ensure_module_state(rpc, name)
        if not mod:
            _logger.warning('  模块 %s 不存在于服务器，跳过', name)
            continue
        if mod['state'] == 'installed':
            installed.append(name)
            _logger.info('  [已装] %s', name)
        elif mod['state'] in ('uninstalled', 'to install'):
            to_install.append((name, mod['id']))
        else:
            _logger.warning('  模块 %s 状态异常: %s', name, mod['state'])

    for name, mid in to_install:
        _logger.info('  安装 %s ...', name)
        t0 = time.time()
        for attempt in range(8):
            try:
                rpc.call('ir.module.module', 'button_immediate_install', [[mid]])
                break
            except RuntimeError as e:
                if 'processing a scheduled action' in str(e) and attempt < 7:
                    _logger.info('    服务端忙，%d 秒后重试 (%d/7)...', 5, attempt + 1)
                    time.sleep(5)
                else:
                    raise
        _logger.info('  安装 %s 完成 (%.1fs)', name, time.time() - t0)
    _logger.info('Phase 1 完成: 已装 %d, 新装 %d', len(installed), len(to_install))


# ============================= Phase 2: QMS/PLM 动态建模 =============================

# 检验类型通用选项
INSP_TYPE_SELECTION = [
    ('iqc', '来料检验 IQC'), ('ipqc', '制程检验 IPQC'),
    ('fqc', '成品检验 FQC'), ('oqc', '出货检验 OQC'),
]

def sel_vals(model, field, pairs):
    """为 manual selection 字段创建选项 (ir.model.fields.selection)"""
    return pairs

def phase_models(rpc):
    _logger.info('===== Phase 2: 创建 QMS/PLM 动态模型 =====')

    def make_model(name, description, fields_spec):
        """fields_spec: list of dicts(ir.model.fields create vals, 不含 model_id/model)
        支持特殊键 'default'（字段默认值，通过 ir.default 设置）"""
        mid, created = get_or_create(rpc, 'ir.model',
                                     [('model', '=', name)],
                                     {'name': description, 'model': name, 'state': 'manual'})
        if not created:
            _logger.info('  模型 %s 已存在 (id=%s)', name, mid)
        else:
            _logger.info('  创建模型 %s (id=%s)', name, mid)
        for fspec in fields_spec:
            fdomain = [('model', '=', name), ('name', '=', fspec['name'])]
            existing = rpc.search_count('ir.model.fields', fdomain)
            if existing:
                continue
            vals = dict(fspec)
            default_val = vals.pop('default', None)
            vals.update({'model_id': mid, 'model': name, 'state': 'manual'})
            rpc.create('ir.model.fields', vals)
            if default_val is not None:
                rpc.call('ir.default', 'set', [name, fspec['name'], default_val])
        return mid

    # ---------- qc.inspection 检验单 ----------
    mid_insp = make_model('x_qc_inspection', '质量检验单', [
        {'name': 'x_name', 'field_description': '单号', 'ttype': 'char',
         'readonly': True, 'copied': False},
        {'name': 'x_inspection_type', 'field_description': '检验类型',
         'ttype': 'selection', 'selection': INSP_TYPE_SELECTION, 'required': True},
        {'name': 'x_product_id', 'field_description': '产品', 'ttype': 'many2one',
         'relation': 'product.product', 'required': True, 'on_delete': 'restrict'},
        {'name': 'x_partner_id', 'field_description': '供应商/客户', 'ttype': 'many2one',
         'relation': 'res.partner'},
        {'name': 'x_lot_id', 'field_description': '批次', 'ttype': 'many2one',
         'relation': 'stock.lot'},
        {'name': 'x_mo_id', 'field_description': '生产工单', 'ttype': 'many2one',
         'relation': 'mrp.production'},
        {'name': 'x_picking_id', 'field_description': '收发货单', 'ttype': 'many2one',
         'relation': 'stock.picking'},
        {'name': 'x_qty', 'field_description': '送检数量', 'ttype': 'float', 'required': True},
        {'name': 'x_sample_qty', 'field_description': '抽样数量', 'ttype': 'float'},
        {'name': 'x_result', 'field_description': '检验结论',
         'ttype': 'selection', 'selection': [
             ('pending', '待检'), ('pass', '合格'), ('fail', '不合格'), ('conditional', '让步接收')],
         'default': 'pending'},
        {'name': 'x_inspector_id', 'field_description': '检验员', 'ttype': 'many2one',
         'relation': 'res.users'},
        {'name': 'x_inspection_date', 'field_description': '检验日期', 'ttype': 'datetime'},
        {'name': 'x_state', 'field_description': '状态',
         'ttype': 'selection', 'selection': [
             ('draft', '草稿'), ('doing', '检验中'), ('done', '已完成'), ('cancelled', '已取消')],
         'default': 'draft'},
        {'name': 'x_note', 'field_description': '备注', 'ttype': 'text'},
    ])

    # ---------- qc.inspection.line 检验项目行 ----------
    make_model('x_qc_inspection_line', '检验项目行', [
        {'name': 'x_inspection_id', 'field_description': '检验单', 'ttype': 'many2one',
         'relation': 'x_qc_inspection', 'on_delete': 'cascade', 'required': True},
        {'name': 'x_sequence', 'field_description': '序号', 'ttype': 'integer'},
        {'name': 'x_name', 'field_description': '检验项目', 'ttype': 'char', 'required': True},
        {'name': 'x_standard', 'field_description': '规格标准', 'ttype': 'char'},
        {'name': 'x_actual', 'field_description': '实测值', 'ttype': 'char'},
        {'name': 'x_result', 'field_description': '单项结论',
         'ttype': 'selection', 'selection': [
             ('na', '不适用'), ('pass', '合格'), ('fail', '不合格')]},
        {'name': 'x_note', 'field_description': '备注', 'ttype': 'char'},
    ])

    # one2many 需在行模型的 many2one 存在后创建
    o2m_insp_lines = {'name': 'x_line_ids', 'field_description': '检验项目',
                      'ttype': 'one2many', 'relation': 'x_qc_inspection_line',
                      'relation_field': 'x_inspection_id'}
    existing = rpc.search_count('ir.model.fields',
                                [('model', '=', 'x_qc_inspection'), ('name', '=', 'x_line_ids')])
    if not existing:
        vals = dict(o2m_insp_lines, model_id=mid_insp, model='x_qc_inspection', state='manual')
        rpc.create('ir.model.fields', vals)

    # ---------- qc.ncr 不合格品处置单 ----------
    mid_ncr = make_model('x_qc_ncr', '不合格品处置单', [
        {'name': 'x_name', 'field_description': '单号', 'ttype': 'char',
         'readonly': True, 'copied': False},
        {'name': 'x_inspection_id', 'field_description': '来源检验单', 'ttype': 'many2one',
         'relation': 'x_qc_inspection', 'on_delete': 'set null'},
        {'name': 'x_product_id', 'field_description': '产品', 'ttype': 'many2one',
         'relation': 'product.product', 'required': True, 'on_delete': 'restrict'},
        {'name': 'x_qty_defect', 'field_description': '不合格数量', 'ttype': 'float', 'required': True},
        {'name': 'x_disposition', 'field_description': '处置方式',
         'ttype': 'selection', 'selection': [
             ('return', '退货'), ('rework', '返工/返修'),
             ('accept', '让步接收'), ('scrap', '报废')]},
        {'name': 'x_state', 'field_description': '状态',
         'ttype': 'selection', 'selection': [
             ('draft', '草稿'), ('processing', '处置中'), ('done', '已闭环')],
         'default': 'draft'},
        {'name': 'x_root_cause', 'field_description': '原因分析', 'ttype': 'text'},
        {'name': 'x_action', 'field_description': '处置措施', 'ttype': 'text'},
        {'name': 'x_responsible_id', 'field_description': '责任人', 'ttype': 'many2one',
         'relation': 'res.users'},
        {'name': 'x_date_done', 'field_description': '闭环日期', 'ttype': 'datetime'},
    ])

    # ---------- plm.eco 工程变更单 ----------
    mid_eco = make_model('x_plm_eco', '工程变更单 ECO', [
        {'name': 'x_name', 'field_description': '单号', 'ttype': 'char',
         'readonly': True, 'copied': False},
        {'name': 'x_title', 'field_description': '变更主题', 'ttype': 'char', 'required': True},
        {'name': 'x_origin', 'field_description': '变更来源',
         'ttype': 'selection', 'selection': [
             ('customer', '客户要求'), ('quality', '质量改进'), ('cost', '成本优化'),
             ('design', '设计优化'), ('process', '工艺改进'), ('other', '其他')]},
        {'name': 'x_priority', 'field_description': '优先级',
         'ttype': 'selection', 'selection': [
             ('low', '低'), ('normal', '中'), ('high', '高'), ('urgent', '紧急')],
         'default': 'normal'},
        {'name': 'x_product_tmpl_id', 'field_description': '产品', 'ttype': 'many2one',
         'relation': 'product.template'},
        {'name': 'x_bom_id', 'field_description': '物料清单 BOM', 'ttype': 'many2one',
         'relation': 'mrp.bom'},
        {'name': 'x_change_desc', 'field_description': '变更内容', 'ttype': 'text', 'required': True},
        {'name': 'x_reason', 'field_description': '变更原因', 'ttype': 'text'},
        {'name': 'x_impact', 'field_description': '影响分析', 'ttype': 'text'},
        {'name': 'x_effective_date', 'field_description': '生效日期', 'ttype': 'date'},
        {'name': 'x_state', 'field_description': '状态',
         'ttype': 'selection', 'selection': [
             ('draft', '草稿'), ('submitted', '已提交'), ('approved', '已批准'),
             ('implemented', '已实施'), ('cancelled', '已取消')],
         'default': 'draft'},
        {'name': 'x_requester_id', 'field_description': '申请人', 'ttype': 'many2one',
         'relation': 'res.users'},
        {'name': 'x_approver_id', 'field_description': '批准人', 'ttype': 'many2one',
         'relation': 'res.users'},
        {'name': 'x_implementer_id', 'field_description': '实施人', 'ttype': 'many2one',
         'relation': 'res.users'},
        {'name': 'x_new_bom_rev', 'field_description': '新 BOM 版本', 'ttype': 'char'},
    ])

    # ---------- 权限 ir.access ----------
    _logger.info('  配置 ir.access 权限...')
    group_user = rpc.ref('base.group_user')
    for model_name, model_id in [('x_qc_inspection', mid_insp), ('x_qc_ncr', mid_ncr),
                                 ('x_plm_eco', mid_eco)]:
        exists = rpc.search_count('ir.access', [('model_id', '=', model_id)])
        if exists:
            continue
        rpc.create('ir.access', {
            'name': '%s 全员读写' % model_name,
            'model_id': model_id,
            'group_id': group_user,
            'operation': 'crud',
        })
    # 检验行: 跟随主表（全员）
    line_ids = rpc.search('ir.model', [('model', '=', 'x_qc_inspection_line')])
    if line_ids and not rpc.search_count('ir.access', [('model_id', '=', line_ids[0])]):
        rpc.create('ir.access', {
            'name': 'qc.inspection.line 全员读写',
            'model_id': line_ids[0],
            'group_id': group_user,
            'operation': 'crud',
        })

    _create_ncr_o2m(rpc, mid_ncr, mid_insp)
    action_ids = _create_server_actions(rpc)
    _create_views(rpc, action_ids)
    _create_menus(rpc, mid_insp, mid_ncr, mid_eco)
    _create_sequences(rpc)
    _create_automations(rpc)


# ---------- 视图 ----------
VIEW_ARCH = {
    'x_qc_inspection': {
        'form': """<form string="质量检验单">
    <header>
        <button name="%ACTION_insp_start%" type="action" string="开始检验" class="oe_highlight"
                invisible="x_state != 'draft'"/>
        <button name="%ACTION_insp_done%" type="action" string="完成检验" class="oe_highlight"
                invisible="x_state != 'doing'"/>
        <button name="%ACTION_insp_cancel%" type="action" string="取消" invisible="x_state in ('done', 'cancelled')"/>
        <field name="x_state" widget="statusbar" statusbar_visible="draft,doing,done"/>
    </header>
    <sheet>
        <div class="oe_button_box" name="button_box">
            <button name="%ACTION_insp_view_ncr%" type="action" class="oe_stat_button" icon="fa-exclamation-triangle">
                <field name="x_ncr_count" widget="statinfo" string="不合格品处置"/>
            </button>
        </div>
        <div class="oe_title">
            <h1><field name="x_name" placeholder="保存后自动生成单号"/></h1>
        </div>
        <group>
            <group string="检验信息">
                <field name="x_inspection_type"/>
                <field name="x_product_id"/>
                <field name="x_lot_id" invisible="not x_lot_id"/>
                <field name="x_qty"/>
                <field name="x_sample_qty"/>
            </group>
            <group string="来源与结论">
                <field name="x_partner_id"/>
                <field name="x_mo_id" invisible="not x_mo_id"/>
                <field name="x_picking_id" invisible="not x_picking_id"/>
                <field name="x_result"/>
                <field name="x_inspector_id"/>
                <field name="x_inspection_date"/>
            </group>
        </group>
        <notebook>
            <page string="检验项目">
                <field name="x_line_ids">
                    <list editable="bottom">
                        <field name="x_sequence" widget="handle"/>
                        <field name="x_name"/>
                        <field name="x_standard"/>
                        <field name="x_actual"/>
                        <field name="x_result"/>
                        <field name="x_note"/>
                    </list>
                </field>
            </page>
            <page string="不合格品处置">
                <field name="x_ncr_ids">
                    <list>
                        <field name="x_name"/>
                        <field name="x_disposition"/>
                        <field name="x_qty_defect"/>
                        <field name="x_state"/>
                    </list>
                </field>
            </page>
            <page string="备注">
                <field name="x_note"/>
            </page>
        </notebook>
    </sheet>
</form>""",
        'list': """<list string="检验单" decoration-info="x_state == 'draft'"
              decoration-success="x_result == 'pass'" decoration-danger="x_result == 'fail'">
    <field name="x_name"/>
    <field name="x_inspection_type"/>
    <field name="x_product_id"/>
    <field name="x_qty"/>
    <field name="x_result"/>
    <field name="x_inspector_id"/>
    <field name="x_inspection_date" optional="show"/>
    <field name="x_state" widget="badge"
           decoration-info="x_state in ('draft','doing')"
           decoration-success="x_state == 'done'"/>
</list>""",
        'search': """<search string="搜索检验单">
    <field name="x_name" string="单号"/>
    <field name="x_product_id" string="产品"/>
    <filter name="iqc" string="来料检验" domain="[('x_inspection_type','=','iqc')]"/>
    <filter name="ipqc" string="制程检验" domain="[('x_inspection_type','=','ipqc')]"/>
    <filter name="fqc" string="成品检验" domain="[('x_inspection_type','=','fqc')]"/>
    <filter name="oqc" string="出货检验" domain="[('x_inspection_type','=','oqc')]"/>
    <separator/>
    <filter name="fail" string="不合格" domain="[('x_result','=','fail')]"/>
    <filter name="pending" string="待检" domain="[('x_result','=','pending')]"/>
    <separator/>
    <filter name="draft" string="草稿" domain="[('x_state','=','draft')]"/>
    <filter name="done" string="已完成" domain="[('x_state','=','done')]"/>
    <searchpanel>
        <field name="x_inspection_type" string="检验类型"/>
        <field name="x_result" string="结论"/>
        <field name="x_inspector_id" string="检验员"/>
    </searchpanel>
</search>""",
    },
    'x_qc_ncr': {
        'form': """<form string="不合格品处置单">
    <header>
        <button name="%ACTION_ncr_process%" type="action" string="开始处置" class="oe_highlight"
                invisible="x_state != 'draft'"/>
        <button name="%ACTION_ncr_close%" type="action" string="闭环" class="oe_highlight"
                invisible="x_state != 'processing'"/>
        <field name="x_state" widget="statusbar" statusbar_visible="draft,processing,done"/>
    </header>
    <sheet>
        <div class="oe_title"><h1><field name="x_name"/></h1></div>
        <group>
            <group string="基本信息">
                <field name="x_inspection_id"/>
                <field name="x_product_id"/>
                <field name="x_qty_defect"/>
                <field name="x_disposition"/>
            </group>
            <group string="处置跟踪">
                <field name="x_responsible_id"/>
                <field name="x_date_done" readonly="x_state != 'processing'"/>
            </group>
        </group>
        <group string="分析">
            <field name="x_root_cause" placeholder="原因分析（人机料法环）"/>
            <field name="x_action" placeholder="处置措施与纠正预防措施"/>
        </group>
    </sheet>
</form>""",
        'list': """<list string="不合格品处置单" decoration-danger="x_state != 'done'">
    <field name="x_name"/>
    <field name="x_product_id"/>
    <field name="x_qty_defect"/>
    <field name="x_disposition"/>
    <field name="x_responsible_id"/>
    <field name="x_state" widget="badge"
           decoration-info="x_state == 'draft'" decoration-warning="x_state == 'processing'"
           decoration-success="x_state == 'done'"/>
</list>""",
        'search': """<search string="搜索处置单">
    <field name="x_name"/>
    <field name="x_product_id"/>
    <filter name="open" string="未闭环" domain="[('x_state','!=','done')]"/>
    <filter name="return" string="退货" domain="[('x_disposition','=','return')]"/>
    <filter name="rework" string="返工" domain="[('x_disposition','=','rework')]"/>
    <searchpanel>
        <field name="x_disposition" string="处置方式"/>
        <field name="x_state" string="状态"/>
    </searchpanel>
</search>""",
    },
    'x_plm_eco': {
        'form': """<form string="工程变更单">
    <header>
        <button name="%ACTION_eco_submit%" type="action" string="提交审批" class="oe_highlight"
                invisible="x_state != 'draft'"/>
        <button name="%ACTION_eco_approve%" type="action" string="批准" class="oe_highlight"
                invisible="x_state != 'submitted'"/>
        <button name="%ACTION_eco_implement%" type="action" string="确认实施" class="oe_highlight"
                invisible="x_state != 'approved'"/>
        <button name="%ACTION_eco_cancel%" type="action" string="取消"
                invisible="x_state in ('implemented', 'cancelled')"/>
        <field name="x_state" widget="statusbar"
               statusbar_visible="draft,submitted,approved,implemented"/>
    </header>
    <sheet>
        <div class="oe_title">
            <h1><field name="x_name" placeholder="保存后自动生成单号"/></h1>
            <h3><field name="x_title" placeholder="变更主题"/></h3>
        </div>
        <group>
            <group string="变更信息">
                <field name="x_origin"/>
                <field name="x_priority"/>
                <field name="x_requester_id"/>
                <field name="x_approver_id"/>
                <field name="x_implementer_id"/>
            </group>
            <group string="影响对象">
                <field name="x_product_tmpl_id"/>
                <field name="x_bom_id" domain="[('product_tmpl_id','=',x_product_tmpl_id)]"/>
                <field name="x_new_bom_rev"/>
                <field name="x_effective_date"/>
            </group>
        </group>
        <notebook>
            <page string="变更内容">
                <field name="x_change_desc" placeholder="具体变更内容（材料/工艺/图纸/尺寸…）"/>
            </page>
            <page string="变更原因">
                <field name="x_reason"/>
            </page>
            <page string="影响分析">
                <field name="x_impact" placeholder="对库存、在制、成本、客户的影响评估"/>
            </page>
        </notebook>
    </sheet>
</form>""",
        'list': """<list string="工程变更单" decoration-muted="x_state == 'cancelled'"
              decoration-info="x_state == 'draft'" decoration-warning="x_state in ('submitted','approved')">
    <field name="x_name"/>
    <field name="x_title"/>
    <field name="x_origin"/>
    <field name="x_product_tmpl_id" optional="show"/>
    <field name="x_priority" widget="badge"
           decoration-success="x_priority in ('low','normal')"
           decoration-warning="x_priority == 'high'" decoration-danger="x_priority == 'urgent'"/>
    <field name="x_requester_id" optional="show"/>
    <field name="x_state" widget="badge"
           decoration-info="x_state in ('draft','submitted')"
           decoration-success="x_state == 'implemented'"/>
</list>""",
        'search': """<search string="搜索工程变更单">
    <field name="x_name"/>
    <field name="x_title"/>
    <field name="x_product_tmpl_id"/>
    <filter name="my" string="我申请的" domain="[('x_requester_id','=',uid)]"/>
    <separator/>
    <filter name="draft" string="草稿" domain="[('x_state','=','draft')]"/>
    <filter name="submitted" string="待批" domain="[('x_state','=','submitted')]"/>
    <filter name="implemented" string="已实施" domain="[('x_state','=','implemented')]"/>
    <searchpanel>
        <field name="x_state" string="状态"/>
        <field name="x_origin" string="变更来源"/>
    </searchpanel>
</search>""",
    },
}


def _create_views(rpc, action_ids):
    _logger.info('  创建视图...')
    for model_name, views in VIEW_ARCH.items():
        mid = rpc.search('ir.model', [('model', '=', model_name)], limit=1)[0]
        for vtype, arch in views.items():
            exists = rpc.search_count('ir.ui.view', [
                ('model', '=', model_name), ('type', '=', vtype), ('name', '=', '%s.view.%s' % (model_name, vtype))])
            if exists:
                continue
            # 注入 server action id
            for key, aid in action_ids.items():
                arch = arch.replace('%%ACTION_%s%%' % key, str(aid))
            rpc.create('ir.ui.view', {
                'name': '%s.view.%s' % (model_name, vtype),
                'model': model_name,
                'model_id': mid,
                'type': vtype,
                'arch_db': arch,
                'mode': 'primary',
            })
            _logger.info('    视图 %s (%s)', model_name, vtype)


def _create_menus(rpc, mid_insp, mid_ncr, mid_eco):
    _logger.info('  创建动作与菜单...')
    ACTIONS = [
        ('action_qc_inspection', '检验单', 'x_qc_inspection', mid_insp,
         {'search_view_id_ref': 'qc.inspection.view.search'}),
        ('action_qc_ncr', '不合格品处置', 'x_qc_ncr', mid_ncr, {}),
        ('action_plm_eco', '工程变更单', 'x_plm_eco', mid_eco, {}),
    ]
    for act_name, label, model, model_id, _extra in ACTIONS:
        exists = rpc.search('ir.actions.act_window', [('name', '=', label), ('res_model', '=', model)], limit=1)
        if not exists:
            rpc.create('ir.actions.act_window', {
                'name': label,
                'res_model': model,
                'view_mode': 'list,form',
            })

    def ensure_menu(name, vals, parent=None):
        domain = [('name', '=', name)]
        if parent:
            domain.append(('parent_id', '=', parent))
        else:
            domain.append(('parent_id', '=', False))
        ids = rpc.search('ir.ui.menu', domain, limit=1)
        if ids:
            return ids[0]
        if parent:
            vals = dict(vals, parent_id=parent)
        return rpc.create('ir.ui.menu', vals)

    # 顶级菜单
    m_qc = ensure_menu('质量管理', {'name': '质量管理'})
    m_plm = ensure_menu('研发管理', {'name': '研发管理'})

    # 子菜单（带动作）
    def ensure_menu_action(name, action_model, action_name, parent):
        ids = rpc.search('ir.ui.menu', [('name', '=', name), ('parent_id', '=', parent)], limit=1)
        if ids:
            return ids[0]
        act_ids = rpc.search('ir.actions.act_window',
                             [('name', '=', action_name), ('res_model', '=', action_model)], limit=1)
        return rpc.create('ir.ui.menu', {
            'name': name, 'parent_id': parent, 'action': 'ir.actions.act_window,%s' % act_ids[0],
        })

    ensure_menu_action('检验单', 'x_qc_inspection', '检验单', m_qc)
    ensure_menu_action('不合格品处置', 'x_qc_ncr', '不合格品处置', m_qc)
    ensure_menu_action('工程变更单', 'x_plm_eco', '工程变更单', m_plm)
    _logger.info('    菜单: 质量管理 / 研发管理')


def _create_sequences(rpc):
    _logger.info('  创建序列...')
    seqs = [
        ('qc.inspection.iqc', '检验单-来料', 'QC/IQC/%(y)s/'),
        ('qc.inspection.ipqc', '检验单-制程', 'QC/IPQC/%(y)s/'),
        ('qc.inspection.fqc', '检验单-成品', 'QC/FQC/%(y)s/'),
        ('qc.inspection.oqc', '检验单-出货', 'QC/OQC/%(y)s/'),
        ('x_qc_ncr', '不合格品处置单', 'QC/NCR/%(y)s/'),
        ('x_plm_eco', '工程变更单', 'ECO/%(y)s/'),
    ]
    for code, name, prefix in seqs:
        if not rpc.search('ir.sequence', [('code', '=', code)], limit=1):
            rpc.create('ir.sequence', {
                'name': name, 'code': code, 'prefix': prefix,
                'padding': 4, 'company_id': False,
            })


def _create_automations(rpc):
    _logger.info('  创建自动化规则...')
    insp_id = rpc.search('ir.model', [('model', '=', 'x_qc_inspection')], limit=1)[0]
    ncr_id = rpc.search('ir.model', [('model', '=', 'x_qc_ncr')], limit=1)[0]
    eco_id = rpc.search('ir.model', [('model', '=', 'x_plm_eco')], limit=1)[0]

    # 检验单: 单号 + 默认检验项
    code_insp = """
for rec in records:
    if not rec.x_name:
        prefix_code = 'qc.inspection.' + (rec.x_inspection_type or 'iqc')
        rec.write({'x_name': env['ir.sequence'].next_by_code(prefix_code)})
    if not rec.x_line_ids:
        templates = {
            'iqc': [('外观/色差', '无明显色差、划伤、脏污'), ('材质验证', '与样品/订单要求一致'),
                    ('厚度/尺寸', '在图纸公差范围内'), ('包装标识', '标识清晰、数量准确')],
            'ipqc': [('首件确认', '首件合格后量产'), ('针距密度', '针距均匀符合工艺标准'),
                     ('帮面成型', '成型饱满、对称'), ('胶合强度', '无开胶、溢胶')],
            'fqc': [('外观全检', '无缺陷'), ('配双成对', '左右脚对称、色泽一致'),
                    ('尺寸复核', '楦长/跖围达标'), ('清洁度', '无胶渍、线头')],
            'oqc': [('包装核对', '按装箱单核对'), ('标签标识', '条码/吊牌/鞋盒正确'),
                    ('数量清点', '与出货单一致'), ('装箱规范', '封箱牢固、防潮措施')],
        }
        items = templates.get(rec.x_inspection_type, [])
        for seq, (nm, std) in enumerate(items, start=1):
            env['x_qc_inspection_line'].create({
                'x_inspection_id': rec.id, 'x_sequence': seq,
                'x_name': nm, 'x_standard': std, 'x_result': 'na'})
"""
    _ensure_automation(rpc, '检验单：自动编号与检验项', insp_id, code_insp)

    code_ncr = """
for rec in records:
    if not rec.x_name:
        rec.write({'x_name': env['ir.sequence'].next_by_code('x_qc_ncr')})
"""
    _ensure_automation(rpc, 'NCR：自动编号', ncr_id, code_ncr)

    code_eco = """
for rec in records:
    if not rec.x_name:
        rec.write({'x_name': env['ir.sequence'].next_by_code('x_plm_eco')})
"""
    _ensure_automation(rpc, 'ECO：自动编号', eco_id, code_eco)


def _ensure_automation(rpc, name, model_id, code):
    if rpc.search('base.automation', [('name', '=', name)], limit=1):
        return
    rpc.create('base.automation', {
        'name': name,
        'model_id': model_id,
        'trigger': 'on_create',
        'action_server_ids': [(0, 0, {
            'name': name,
            'model_id': model_id,
            'state': 'code',
            'code': code,
        })],
    })
    _logger.info('    自动化: %s', name)


def _create_ncr_o2m(rpc, mid_ncr, mid_insp):
    """ncr_ids / ncr_count 字段（qc.inspection 上的 one2many + compute 计数）"""
    existing = rpc.search_count('ir.model.fields',
                                [('model', '=', 'x_qc_inspection'), ('name', '=', 'x_ncr_ids')])
    if not existing:
        rpc.create('ir.model.fields', {
            'name': 'x_ncr_ids', 'field_description': '不合格品处置单', 'ttype': 'one2many',
            'relation': 'x_qc_ncr', 'relation_field': 'x_inspection_id',
            'model_id': mid_insp, 'model': 'x_qc_inspection', 'state': 'manual'})
    existing = rpc.search_count('ir.model.fields',
                                [('model', '=', 'x_qc_inspection'), ('name', '=', 'x_ncr_count')])
    if not existing:
        rpc.create('ir.model.fields', {
            'name': 'x_ncr_count', 'field_description': '处置单数量', 'ttype': 'integer',
            'compute': "for rec in self:\n    rec.update({'x_ncr_count': len(rec.x_ncr_ids)})",
            'depends': 'x_ncr_ids', 'store': True,
            'readonly': True, 'copied': False,
            'model_id': mid_insp, 'model': 'x_qc_inspection', 'state': 'manual'})


# ---------- 状态流转 server actions（manual 模型无 Python 方法，用 action 实现） ----------
SERVER_ACTIONS = [
    # (key, name, model, code)
    ('insp_start', '检验单：开始检验', 'x_qc_inspection',
     "records.write({'x_state': 'doing'})"),
    ('insp_done', '检验单：完成检验', 'x_qc_inspection',
     "records.write({'x_state': 'done', 'x_inspection_date': datetime.datetime.now()})"),
    ('insp_cancel', '检验单：取消', 'x_qc_inspection',
     "records.write({'x_state': 'cancelled'})"),
    ('insp_view_ncr', '检验单：查看处置单', 'x_qc_inspection',
     "action = {'type': 'ir.actions.act_window', 'name': '不合格品处置', 'res_model': 'x_qc_ncr',"
     " 'view_mode': 'list,form', 'domain': [('x_inspection_id', 'in', records.ids)]}"),
    ('ncr_process', 'NCR：开始处置', 'x_qc_ncr',
     "records.write({'x_state': 'processing'})"),
    ('ncr_close', 'NCR：闭环', 'x_qc_ncr',
     "records.write({'x_state': 'done', 'x_date_done': datetime.datetime.now()})"),
    ('eco_submit', 'ECO：提交审批', 'x_plm_eco',
     "records.write({'x_state': 'submitted'})"),
    ('eco_approve', 'ECO：批准', 'x_plm_eco',
     "records.write({'x_state': 'approved', 'x_approver_id': env.user.id})"),
    ('eco_implement', 'ECO：确认实施', 'x_plm_eco',
     "records.write({'x_state': 'implemented', 'x_implementer_id': env.user.id})"),
    ('eco_cancel', 'ECO：取消', 'x_plm_eco',
     "records.write({'x_state': 'cancelled'})"),
]


def _create_server_actions(rpc):
    """创建状态流转 server action，返回 {key: id}"""
    _logger.info('  创建状态流转动作...')
    action_ids = {}
    for key, name, model, code in SERVER_ACTIONS:
        ids = rpc.search('ir.actions.server', [('name', '=', name), ('model_id.model', '=', model)], limit=1)
        if ids:
            action_ids[key] = ids[0]
            continue
        mid = rpc.search('ir.model', [('model', '=', model)], limit=1)[0]
        action_ids[key] = rpc.create('ir.actions.server', {
            'name': name, 'model_id': mid, 'state': 'code', 'code': code,
        })
    return action_ids


# ============================= Phase 3: 鞋厂主数据 =============================

def phase_data(rpc):
    _logger.info('===== Phase 3: 鞋厂主数据 =====')

    def goc(model, domain, vals, order=None):
        rid, created = get_or_create(rpc, model, domain, vals, order)
        return rid

    # 1. 计量单位
    uom_pair = goc('uom.uom', [('name', '=', '双')], {'name': '双', 'relative_factor': 1.0})
    uom_m = rpc.ref('uom.product_uom_meter')
    uom_kg = rpc.ref('uom.product_uom_kgm')
    uom_unit = rpc.ref('uom.product_uom_unit')
    _logger.info('  计量单位 OK')

    # 2. 产品分类
    cat_ids = {}
    for name in ['面料', '底材', '辅料', '包装材料', '半成品', '成品鞋']:
        cat_ids[name] = goc('product.category', [('name', '=', name), ('parent_id', '=', False)],
                            {'name': name})
    _logger.info('  产品分类 OK')

    # 3. 库位
    wh_id = rpc.ref('stock.stock_location_stock')
    wh = rpc.read('stock.location', [wh_id], ['complete_name'])[0]
    loc_ids = {}
    for name in ['原材料库-面料', '原材料库-底材', '原材料库-辅料', '待检区', '不合格品区',
                 '半成品库', '成品库', '包装材料库']:
        loc_ids[name] = goc('stock.location',
                            [('complete_name', '=', '%s/%s' % (wh['complete_name'], name))],
                            {'name': name, 'location_id': wh_id})
    _logger.info('  库位 OK')

    # 4. 工作中心
    wc_ids = {}
    for name, note, cost in [('裁断车间', '自动裁断机', 60), ('针车一线', '针车工位 20 个', 25),
                             ('成型一线', '前帮机/中后帮机', 40), ('底部压合组', '压底机 3 台', 30),
                             ('包装组', '包装台 4 组', 15)]:
        wc_ids[name] = goc('mrp.workcenter', [('name', '=', name)],
                           {'name': name, 'note': note, 'time_efficiency': 100, 'costs_hour': cost})
    _logger.info('  工作中心 OK')

    # 5. 产品
    def product(name, cat, uom, **kw):
        storable = kw.pop('storable', True)
        consu = kw.pop('consu', False)
        vals = {
            'name': name, 'categ_id': cat, 'uom_id': uom,
            'type': 'consu',
            'is_storable': False if consu else storable,
            'default_code': kw.pop('code', False),
            'list_price': kw.pop('sale', 0), 'standard_price': kw.pop('cost', 0),
            'purchase_ok': kw.pop('buy', True), 'sale_ok': kw.pop('sell', False),
            'tracking': kw.pop('tracking', False),
            'description': kw.pop('description', False),
        }
        vals.update(kw)
        tmpl_id = goc('product.template', [('name', '=', name)], vals)
        return rpc.read('product.template', [tmpl_id], ['product_variant_id'])[0]['product_variant_id'][0]

    leather = product('头层牛皮-黑色', cat_ids['面料'], uom_m, code='ML-LEA-001', cost=28,
                      description='鞋面用头层牛皮，厚度1.4-1.6mm')
    lining = product('针织内里布-黑色', cat_ids['面料'], uom_m, code='ML-LIN-001', cost=6,
                     description='鞋腔内里，透气针织布')
    outsole = product('橡胶大底-男休闲款', cat_ids['底材'], uom_unit, code='ML-OSO-001', cost=12,
                      description='耐磨橡胶注塑大底')
    midsole = product('EVA中底-男休闲款', cat_ids['底材'], uom_unit, code='ML-MSO-001', cost=5)
    insole = product('乳胶鞋垫-男款', cat_ids['辅料'], uom_unit, code='ML-INS-001', cost=3)
    last = product('鞋楦-男休闲42码', cat_ids['辅料'], uom_pair, code='ML-LST-042', cost=85,
                   consu=True, description='工装鞋楦，可循环使用')
    glue = product('环保水性胶水', cat_ids['辅料'], uom_kg, code='ML-GLU-001', cost=35)
    thread = product('涤纶缝纫线-黑', cat_ids['辅料'], uom_unit, code='ML-THR-001', cost=2)
    lace = product('圆头鞋带-黑-120cm', cat_ids['辅料'], uom_unit, code='ML-LAC-001', cost=0.5)
    shoebox = product('鞋盒-男休闲款', cat_ids['包装材料'], uom_unit, code='PK-BOX-001', cost=2.5)
    _ = product('外箱-双层瓦楞', cat_ids['包装材料'], uom_unit, code='PK-CTN-001', cost=4)
    shoe_tmpl = goc('product.template', [('name', '=', '男士休闲皮鞋-黑-42码')], {
        'name': '男士休闲皮鞋-黑-42码', 'categ_id': cat_ids['成品鞋'], 'uom_id': uom_pair,
        'type': 'consu', 'is_storable': True, 'default_code': 'FG-SHO-042',
        'list_price': 399, 'standard_price': 98, 'purchase_ok': False, 'sale_ok': True,
        'tracking': 'lot'})
    shoe = rpc.read('product.template', [shoe_tmpl], ['product_variant_id'])[0]['product_variant_id'][0]
    _logger.info('  产品 OK (12 个)')

    # 6. BOM + 工序
    bom_ids = rpc.search('mrp.bom', [('product_tmpl_id', '=', shoe_tmpl)], limit=1)
    if not bom_ids:
        bom_lines = [
            (leather, 0.55), (lining, 0.35), (outsole, 2), (midsole, 2), (insole, 2),
            (last, 1), (glue, 0.08), (thread, 1), (lace, 2), (shoebox, 1),
        ]
        ops = [('裁断', '裁断车间', 8), ('针车', '针车一线', 25), ('绷帮成型', '成型一线', 6),
               ('底部加工', '底部压合组', 5), ('包装', '包装组', 3)]
        bom_id = rpc.create('mrp.bom', {
            'product_tmpl_id': shoe_tmpl,
            'product_qty': 1, 'uom_id': uom_pair,
            'type': 'normal', 'code': 'BOM-SHO-042',
            'bom_line_ids': [(0, 0, {'product_id': p, 'product_qty': q}) for p, q in bom_lines],
            'operation_ids': [(0, 0, {
                'name': nm, 'workcenter_id': wc_ids[wc], 'time_cycle_manual': mins,
                'time_mode': 'manual', 'sequence': seq,
            }) for seq, (nm, wc, mins) in enumerate(ops, start=10)],
        })
        _logger.info('  BOM 创建 id=%s (10 行材料 + 5 道工序)', bom_id)

    # 7. 供应商
    for name, street, phone, email in [
        ('广州港汇贸易有限公司', '广州市荔湾区', '020-88886666', 'purchase@ganghui.com'),
        ('温州宏达皮革有限公司', '温州市鹿城区', '0577-88665544', 'sales@hongda-leather.com'),
        ('晋江华利鞋材有限公司', '晋江市陈埭镇', '0595-85123456', 'sales@huali-xc.com'),
    ]:
        goc('res.partner', [('name', '=', name)], {
            'name': name, 'is_company': True, 'street': street, 'phone': phone, 'email': email})
    _logger.info('  供应商 OK')

    # 8. 部门
    for name in ['总经办', '研发部', '生产部', '品质部', '仓储部', '采购部', '销售部', '财务部']:
        goc('hr.department', [('name', '=', name), ('parent_id', '=', False)], {'name': name})
    _logger.info('  部门 OK')

    # 9. 开启批次 + 工单组（当前登录用户）
    uid = rpc.uid
    groups_user = rpc.read('res.users', [uid], ['all_group_ids'])[0]['all_group_ids']
    for gname, gxmlid in [('批次管理', 'stock.group_production_lot'), ('工单/工艺路线', 'mrp.group_mrp_routings')]:
        gid = rpc.ref(gxmlid)
        if gid and gid not in groups_user:
            rpc.call('res.users', 'write', [[uid], {'group_ids': [(4, gid)]}])
            _logger.info('  已为当前用户开启: %s', gname)

    # 10. 关闭新手引导
    rpc.call('ir.config_parameter', 'set_bool', ['web_tour.disable', True])

    # 11. 全厂公告频道
    if not rpc.search('discuss.channel', [('name', '=', '全厂公告')], limit=1):
        group_user_id = rpc.ref('base.group_user')
        rpc.create('discuss.channel', {
            'name': '全厂公告',
            'description': '厂务通知、生产安排、质量通报（全员可见）',
            'channel_type': 'channel',
            'group_public_id': group_user_id,
        })
    _logger.info('  公告频道 OK')

    # 12. 示例来料检验单（走动态模型）
    if not rpc.search('x_qc_inspection', [('x_name', '!=', False)], limit=1):
        partner = rpc.search('res.partner', [('name', '=', '温州宏达皮革有限公司')], limit=1)
        rpc.create('x_qc_inspection', {
            'x_inspection_type': 'iqc',
            'x_product_id': leather,
            'x_qty': 500,
            'x_partner_id': partner[0] if partner else False,
        })
        _logger.info('  示例 IQC 检验单 OK')


# ============================= Phase 4: 验证 =============================

def phase_verify(rpc):
    _logger.info('===== Phase 4: 验证 =====')
    ok = True

    # 模块
    for name in MODULES:
        mod = ensure_module_state(rpc, name)
        st = mod['state'] if mod else 'missing'
        flag = '✓' if st == 'installed' else '✗'
        if st != 'installed':
            ok = False
        _logger.info('  %s 模块 %s: %s', flag, name, st)

    # 动态模型
    for m in ['x_qc_inspection', 'x_qc_inspection_line', 'x_qc_ncr', 'x_plm_eco']:
        cnt = rpc.search_count('ir.model', [('model', '=', m)])
        _logger.info('  %s 模型 %s', '✓' if cnt else '✗', m)
        if not cnt:
            ok = False

    # 菜单
    for menu in ['质量管理', '研发管理']:
        cnt = rpc.search_count('ir.ui.menu', [('name', '=', menu), ('parent_id', '=', False)])
        _logger.info('  %s 菜单 %s', '✓' if cnt else '✗', menu)
        if not cnt:
            ok = False

    # 主数据
    checks = [
        ('product.template', [('default_code', 'in', ['ML-LEA-001', 'FG-SHO-042'])], 2, '鞋厂产品'),
        ('mrp.bom', [('code', '=', 'BOM-SHO-042')], 1, 'BOM'),
        ('mrp.workcenter', [], 5, '工作中心'),
        ('hr.department', [], 8, '部门'),
        ('res.partner', [('name', '=', '广州港汇贸易有限公司')], 1, '供应商'),
    ]
    for model, domain, expect, label in checks:
        cnt = rpc.search_count(model, domain)
        flag = '✓' if cnt >= expect else '✗'
        if cnt < expect:
            ok = False
        _logger.info('  %s %s: %d', flag, label, cnt)

    # 业务流冒烟：创建→自动化触发→读取
    _logger.info('  冒烟测试: 创建 FQC 检验单...')
    shoe_p = rpc.search('product.product', [('default_code', '=', 'FG-SHO-042')], limit=1)
    if shoe_p:
        insp_id = rpc.create('x_qc_inspection', {
            'x_inspection_type': 'fqc', 'x_product_id': shoe_p[0], 'x_qty': 120,
        })
        insp = rpc.read('x_qc_inspection', [insp_id], ['x_name', 'x_line_ids'])[0]
        _logger.info('    检验单 %s, 检验项 %d 条', insp['x_name'], len(insp['x_line_ids']))
        if not insp['x_name'] or not insp['x_line_ids']:
            ok = False
        else:
            # 清理冒烟数据
            rpc.call('x_qc_inspection', 'unlink', [[insp_id]])

    _logger.info('===== 部署验证: %s =====', '全部通过 ✓' if ok else '存在失败项 ✗')
    return ok


# ============================= main =============================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='Odoo 地址')
    parser.add_argument('--db', required=True)
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', required=True)
    parser.add_argument('--phase', default='all',
                        choices=['all', 'modules', 'models', 'data', 'verify'])
    args = parser.parse_args()

    rpc = OdooRPC(args.url, args.db, args.user, args.password)
    rpc.authenticate()

    phases = {
        'modules': phase_modules,
        'models': phase_models,
        'data': phase_data,
        'verify': phase_verify,
    }
    if args.phase == 'all':
        phase_modules(rpc)
        phase_models(rpc)
        phase_data(rpc)
        phase_verify(rpc)
    else:
        phases[args.phase](rpc)

    _logger.info('完成.')


if __name__ == '__main__':
    main()
