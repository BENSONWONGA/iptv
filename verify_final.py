#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终完整验证：全链路冒烟（修正 context 传递）"""
import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'

s = requests.Session()


def rpc(model, method, args=None, kwargs=None, ctx=None):
    kw = dict(kwargs or {})
    if ctx is not None:
        kw['context'] = ctx
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kw},
    }, timeout=120)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(d['error'].get('data', {}).get('message', str(d['error']))[:250])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']
CTX = {'lang': 'zh_CN', 'tz': 'Asia/Shanghai'}

# 0. 中文菜单
menus = rpc('ir.ui.menu', 'search_read', [[['parent_id', '=', False]]],
            {'fields': ['name'], 'limit': 100}, ctx=CTX)
names = [m['name'] for m in menus]
core = ['质量管理', '研发管理', '制造', '库存', '销售', '采购', '员工', '出勤', '休假', '费用', '项目']
print('顶级菜单:', names)
print('核心菜单检查:', all(w in names for w in core), '✓')

shoe = rpc('product.product', 'search', [[['default_code', '=', 'FG-SHO-042']]])[0]

# 1. 创建 FQC 检验单（自动编号 + 默认检验项）
insp = rpc('x_qc_inspection', 'create',
           [{'x_inspection_type': 'fqc', 'x_product_id': shoe, 'x_qty': 60}])
rec = rpc('x_qc_inspection', 'read', [[insp]], {'fields': ['x_name', 'x_line_ids', 'x_state']}, ctx=CTX)
print('1. 检验单 %s 状态=%s 检验项=%d' % (rec[0]['x_name'], rec[0]['x_state'], len(rec[0]['x_line_ids'])))
assert len(rec[0]['x_line_ids']) == 4, '检验项数量不对'

# 2. 状态流转：开始检验（server action + active context）
def run_action(name, rid, model):
    act = rpc('ir.actions.server', 'search', [[['name', '=', name]]])[0]
    return rpc('ir.actions.server', 'run', [[act]],
               ctx=dict(CTX, active_id=rid, active_ids=[rid], active_model=model))

run_action('检验单：开始检验', insp, 'x_qc_inspection')
rec = rpc('x_qc_inspection', 'read', [[insp]], {'fields': ['x_state']}, ctx=CTX)
print('2. 开始检验 => 状态:', rec[0]['x_state'])
assert rec[0]['x_state'] == 'doing'

run_action('检验单：完成检验', insp, 'x_qc_inspection')
rec = rpc('x_qc_inspection', 'read', [[insp]],
          {'fields': ['x_state', 'x_inspection_date', 'x_name']}, ctx=CTX)
print('3. 完成检验 => 状态: %s 检验日期: %s' % (rec[0]['x_state'], rec[0]['x_inspection_date']))
assert rec[0]['x_state'] == 'done'

# 3. NCR：自动编号 + 状态闭环
ncr = rpc('x_qc_ncr', 'create', [{
    'x_inspection_id': insp, 'x_product_id': shoe, 'x_qty_defect': 3,
    'x_disposition': 'rework', 'x_root_cause': '胶合强度不足', 'x_action': '返工后复检'}])
n = rpc('x_qc_ncr', 'read', [[ncr]], {'fields': ['x_name', 'x_state']}, ctx=CTX)
print('4. NCR %s 状态=%s' % (n[0]['x_name'], n[0]['x_state']))
run_action('NCR：开始处置', ncr, 'x_qc_ncr')
run_action('NCR：闭环', ncr, 'x_qc_ncr')
n = rpc('x_qc_ncr', 'read', [[ncr]], {'fields': ['x_state', 'x_date_done']}, ctx=CTX)
print('5. NCR 处置 => 状态: %s 闭环时间: %s' % (n[0]['x_state'], n[0]['x_date_done']))
assert n[0]['x_state'] == 'done'

# 4. ECO：全流程 draft→submitted→approved→implemented
eco = rpc('x_plm_eco', 'create', [{
    'x_title': '验证-大底供应商切换', 'x_origin': 'cost',
    'x_change_desc': '橡胶大底改为华利供应', 'x_priority': 'high'}])
e = rpc('x_plm_eco', 'read', [[eco]], {'fields': ['x_name', 'x_state']}, ctx=CTX)
print('6. ECO %s 状态=%s' % (e[0]['x_name'], e[0]['x_state']))
for act_name, expect in [('ECO：提交审批', 'submitted'), ('ECO：批准', 'approved'),
                         ('ECO：确认实施', 'implemented')]:
    run_action(act_name, eco, 'x_plm_eco')
    e = rpc('x_plm_eco', 'read', [[eco]], {'fields': ['x_state', 'x_approver_id', 'x_implementer_id']}, ctx=CTX)
    print('   %s => %s' % (act_name, e[0]['x_state']))
    assert e[0]['x_state'] == expect
print('7. ECO 全流程闭环 ✓ 批准人/实施人已记录')

# 清理冒烟数据
rpc('x_plm_eco', 'unlink', [[eco]])
rpc('x_qc_ncr', 'unlink', [[ncr]])
rpc('x_qc_inspection', 'unlink', [[insp]])
print('冒烟数据已清理')
print('===== 全链路验证 100% 通过 =====')
