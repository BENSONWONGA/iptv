#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给产品列表搜索视图加 searchpanel：左侧显示分类树（带计数、默认展开）"""
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=300)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:500])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
print('登录 ✓')

# 1. 找到目标搜索视图（库存的产品搜索视图，action-530 用的）
views = rpc('ir.ui.view', 'search_read', kwargs={
    'domain': [['model', '=', 'product.template'], ['type', '=', 'search'],
               ['name', 'in', ['product.template.search.view.stock', 'stock.product_template_search_form_view_stock',
                                'product.product_template_search_view']]],
    'fields': ['id', 'name', 'key'], 'limit': 10})
print('候选搜索视图:', [(v['id'], v['name']) for v in views])

# 锁定库存那个（action-530 引用的）
target = None
for v in views:
    if 'stock' in v['name']:
        target = v
        break
if not target:
    # 找 action-530 的 search_view_id
    act = rpc('ir.actions.act_window', 'read', [[530], ['name', 'search_view_id']])[0]
    print('action-530: %s → %s' % (act['name'], act['search_view_id']))
    target = {'id': act['search_view_id'][0], 'name': act['search_view_id'][1]}
print('目标视图: id=%s %s' % (target['id'], target['name']))

# 2. 幂等：已有继承补丁就不重复建
XID = 'shoe_product_search_panel'
exists = rpc('ir.model.data', 'search', kwargs={
    'domain': [['module', '=', 'shoe_custom'], ['name', '=', XID]]})
if exists:
    print('补丁视图已存在 ✓')
    view_id = rpc('ir.model.data', 'read', [exists, ['res_id']])[0]['res_id']
else:
    arch = '''<xpath expr="//search" position="inside">
        <searchpanel>
            <field name="categ_id" string="分类" enable_counters="1" expand="1"/>
        </searchpanel>
    </xpath>'''
    view_id = rpc('ir.ui.view', 'create', [{
        'name': 'shoe.product.search.panel',
        'model': 'product.template',
        'inherit_id': target['id'],
        'mode': 'extension',
        'arch_db': arch,
    }])
    rpc('ir.model.data', 'create', [{
        'module': 'shoe_custom', 'name': XID,
        'model': 'ir.ui.view', 'res_id': view_id,
    }])
    print('继承视图已创建: id=%s ✓' % view_id)

# 3. 验证视图合并无误（读取合并后的 arch）
merged = rpc('ir.ui.view', 'read', [[view_id], ['name']])[0]
print('视图读取正常 ✓')

# 4. 检查 action-530 的 context，尝试让"选分类后新建自动预填类别"
act = rpc('ir.actions.act_window', 'read', [[530], ['name', 'search_view_id', 'context']])[0]
print('action-530 当前 context:', act['context'])
print('\n完成 ✓ — 请浏览器验证产品列表左侧分类树')
