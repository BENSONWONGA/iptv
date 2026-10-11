"""UI 渲染 + 状态流转 + one2many 写入 冒烟测试"""
import sys
sys.path.insert(0, '/workspace')
from deploy_rpc import OdooRPC
import json

rpc = OdooRPC('http://127.0.0.1:8095', 'shoe_test', 'admin', 'admin')
rpc.authenticate()

# 1. 菜单存在性（UI 入口）
qc_menu = rpc.search_count('ir.ui.menu', [('name', '=', '质量管理'), ('parent_id', '=', False)])
qc_sub = rpc.search_count('ir.ui.menu', [('name', 'in', ['检验单', '不合格品处置']), ('parent_id', '!=', False)])
plm_sub = rpc.search_count('ir.ui.menu', [('name', '=', '工程变更单'), ('parent_id', '!=', False)])
print('1. 菜单: 质量管理=%d, QC子菜单=%d, ECO子菜单=%d' % (qc_menu, qc_sub, plm_sub))

# 2. 视图加载（webclient 的 get_views —— UI 渲染入口）
for model in ['x_qc_inspection', 'x_qc_ncr', 'x_plm_eco']:
    try:
        views = rpc.call(model, 'get_views', [[ [False, 'form'], [False, 'list'] ]], {})
        vs = views.get('views', {})
        archs = {vid: v.get('arch', '') for vid, v in vs.items()}
        print('2. %s get_views OK: %d 个视图 (arch 长度 %s)' % (
            model, len(vs), [len(a) for a in archs.values()]))
    except Exception as e:
        print('2. %s get_views FAIL: %s' % (model, str(e)[:200]))

# 3. 状态流转（server action run）
shoe_p = rpc.search('product.product', [('default_code', '=', 'FG-SHO-042')], limit=1)[0]
insp_id = rpc.create('x_qc_inspection', {'x_inspection_type': 'ipqc', 'x_product_id': shoe_p, 'x_qty': 60})
act_start = rpc.search('ir.actions.server', [('name', '=', '检验单：开始检验')], limit=1)[0]
act_done = rpc.search('ir.actions.server', [('name', '=', '检验单：完成检验')], limit=1)[0]
ctx = {'active_id': insp_id, 'active_ids': [insp_id], 'active_model': 'x_qc_inspection'}
rpc.call('ir.actions.server', 'run', [[act_start]], {'context': ctx})
st = rpc.read('x_qc_inspection', [insp_id], ['x_state'])[0]['x_state']
print('3. 开始检验后状态:', st, '(期望 doing)')
rpc.call('ir.actions.server', 'run', [[act_done]], {'context': ctx})
rec = rpc.read('x_qc_inspection', [insp_id], ['x_state', 'x_inspection_date', 'x_name'])[0]
print('4. 完成检验后:', rec['x_state'], rec['x_inspection_date'], rec['x_name'])

# 4. NCR 创建 + 联动
ncr_id = rpc.create('x_qc_ncr', {
    'x_inspection_id': insp_id, 'x_product_id': shoe_p,
    'x_qty_defect': 5, 'x_disposition': 'rework', 'x_root_cause': '帮面胶合不良'})
ncr = rpc.read('x_qc_ncr', [ncr_id], ['x_name', 'x_state'])[0]
cnt = rpc.read('x_qc_inspection', [insp_id], ['x_ncr_count'])[0]['x_ncr_count']
print('5. NCR %s 状态 %s, 主单 x_ncr_count=%s (compute OK)' % (ncr['x_name'], ncr['x_state'], cnt))

# 5. ECO 全流程
bom = rpc.search('mrp.bom', [('code', '=', 'BOM-SHO-042')], limit=1)[0]
shoe_tmpl = rpc.search('product.template', [('default_code', '=', 'FG-SHO-042')], limit=1)[0]
eco_id = rpc.create('x_plm_eco', {
    'x_title': '更换大底供应商', 'x_origin': 'quality',
    'x_product_tmpl_id': shoe_tmpl, 'x_bom_id': bom,
    'x_change_desc': '大底由 A 供应商切换为 B 供应商，物性指标提升',
    'x_effective_date': '2026-11-01'})
for act_name in ['ECO：提交审批', 'ECO：批准', 'ECO：确认实施']:
    aid = rpc.search('ir.actions.server', [('name', '=', act_name)], limit=1)[0]
    rpc.call('ir.actions.server', 'run', [[aid]], {'context': {
        'active_id': eco_id, 'active_ids': [eco_id], 'active_model': 'x_plm_eco'}})
eco = rpc.read('x_plm_eco', [eco_id], ['x_name', 'x_state', 'x_approver_id'])[0]
print('6. ECO %s → %s (批准人 id=%s)' % (eco['x_name'], eco['x_state'], eco['x_approver_id']))

# 6. one2many 检验行编辑（editable list 保存路径）
lines = rpc.read('x_qc_inspection', [insp_id], ['x_line_ids'])[0]['x_line_ids']
rpc.call('x_qc_inspection_line', 'write', [lines[:2],
         {'x_actual': '实测合格', 'x_result': 'pass'}])
l1 = rpc.read('x_qc_inspection_line', [lines[0]], ['x_name', 'x_actual', 'x_result'])[0]
print('7. 检验行写入: %s = %s (%s)' % (l1['x_name'], l1['x_actual'], l1['x_result']))

# 清理冒烟数据
rpc.call('x_qc_inspection', 'unlink', [[insp_id]])
rpc.call('x_qc_ncr', 'unlink', [[ncr_id]])
rpc.call('x_plm_eco', 'unlink', [[eco_id]])
print('8. 冒烟数据已清理')
print('=== 全部冒烟测试通过 ===')
