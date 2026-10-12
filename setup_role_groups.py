#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""建部门角色权限组（细分应用权限）+ 2 个测试账号"""
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


def group_by_xid(module, name):
    d = rpc('ir.model.data', 'search_read', kwargs={
        'domain': [['module', '=', module], ['name', '=', name], ['model', '=', 'res.groups']],
        'fields': ['res_id'], 'limit': 1})
    if d:
        return d[0]['res_id']
    return None


# ── 1. 权限组分类（ir.module.category 禁止 RPC 创建，组不挂分类）──
cat_id = False
print('跳过权限组分类（系统限制）')

# ── 2. 各应用原子权限组 ──────────────────────────
ATOM = {
    'salesman': ('sales_team', 'group_sale_salesman'),                      # 销售-只看自己
    'salesman_all': ('sales_team', 'group_sale_salesman_all_leads'),        # 销售-看全部
    'sale_admin': ('sales_team', 'group_sale_manager'),                     # 销售-管理员
    'mrp_user': ('mrp', 'group_mrp_user'),                                  # 制造-用户
    'mrp_admin': ('mrp', 'group_mrp_manager'),                              # 制造-管理员
    'stock_user': ('stock', 'group_stock_user'),                            # 库存-用户
    'stock_admin': ('stock', 'group_stock_manager'),                        # 库存-管理员
    'purchase_user': ('purchase', 'group_purchase_user'),                   # 采购-用户
    'purchase_admin': ('purchase', 'group_purchase_manager'),              # 采购-管理员
    'invoice': ('account', 'group_account_invoice'),                        # 开票
    'account_read': ('account', 'group_account_readonly'),                  # 会计-只读
    'account_admin': ('account', 'group_account_manager'),                  # 会计-管理员
    'hr_user': ('hr', 'group_hr_user'),                                     # 员工-用户
    'hr_admin': ('hr', 'group_hr_manager'),                                 # 员工-管理员
    'base_user': ('base', 'group_user'),                                    # 内部用户（基础）
}
atom_ids = {}
for key, (mod, xid) in ATOM.items():
    gid = group_by_xid(mod, xid)
    if gid:
        atom_ids[key] = gid
    else:
        print('  ⚠ 未找到组 %s.%s，跳过' % (mod, xid))

# ── 3. 部门角色组定义 ────────────────────────────
ROLES = {
    '管理层角色': ['sale_admin', 'mrp_admin', 'stock_admin', 'purchase_admin', 'account_admin', 'hr_admin'],
    '业务部角色': ['salesman'],
    '电商部角色': ['salesman_all', 'stock_user'],
    '开发部角色': ['mrp_user', 'stock_user'],
    '材料课角色': ['stock_user', 'purchase_user'],
    '生控部角色': ['mrp_user', 'stock_admin', 'purchase_user'],
    '供应链角色': ['stock_user', 'purchase_user'],
    '生产部角色': ['mrp_user', 'stock_user'],
    '品管部角色': ['mrp_user', 'stock_user'],
    '财务部角色': ['invoice', 'account_read', 'purchase_user'],
    '行政部角色': ['hr_admin'],
}

existing_groups = {g['name']: g['id'] for g in rpc('res.groups', 'search_read', kwargs={'fields': ['name'], 'limit': 300})}
for role, keys in ROLES.items():
    implied = [atom_ids[k] for k in keys if k in atom_ids]
    # 确保 implied 含内部用户组（登录基础）
    if 'base_user' in atom_ids and atom_ids['base_user'] not in implied:
        implied.append(atom_ids['base_user'])
    if role in existing_groups:
        rpc('res.groups', 'write', [[existing_groups[role]], {'implied_ids': [(6, 0, implied)]}])
        print('  角色组已存在并更新: %s (%d 项权限)' % (role, len(implied)))
    else:
        gid = rpc('res.groups', 'create', [{
            'name': role,
            'implied_ids': [(6, 0, implied)],
            'comment': '鞋厂部门角色：自动组合应用权限',
        }])
        existing_groups[role] = gid
        print('  建角色组: %s (id=%s, %d 项权限)' % (role, gid, len(implied)))

# ── 4. 建 2 个测试账号（关联员工档案）────────────
TESTS = [
    {'login': 'yewu_test', 'pwd': 'Aa123456', 'role': '业务部角色', 'emp': '傅新新'},
    {'login': 'shengkong_test', 'pwd': 'Aa123456', 'role': '生控部角色', 'emp': '唐章明'},
]
for t in TESTS:
    ids = rpc('res.users', 'search', kwargs={'domain': [['login', '=', t['login']]]})
    if ids:
        uid = ids[0]
        print('  测试账号已存在: %s' % t['login'])
    else:
        uid = rpc('res.users', 'create', [{
            'name': t['emp'] + '(测试)', 'login': t['login'], 'password': t['pwd'],
            'group_ids': [(6, 0, [existing_groups[t['role']]])],
        }])
        print('  建测试账号: %s / %s → %s' % (t['login'], t['pwd'], t['role']))
    # 关联员工档案
    emp_ids = rpc('hr.employee', 'search', kwargs={'domain': [['name', '=', t['emp']]]})
    if emp_ids:
        rpc('hr.employee', 'write', [emp_ids, {'user_id': uid}])
        print('    已关联员工: %s' % t['emp'])

# ── 5. 输出权限矩阵 ─────────────────────────────
print('\n=== 权限矩阵 ===')
APP_MAP = {
    'sale_admin': '销售管理', 'salesman': '销售(自己)', 'salesman_all': '销售(全部)',
    'mrp_admin': '制造管理', 'mrp_user': '制造',
    'stock_admin': '库存管理', 'stock_user': '库存',
    'purchase_admin': '采购管理', 'purchase_user': '采购',
    'account_admin': '会计管理', 'account_read': '会计只读', 'invoice': '开票',
    'hr_admin': '员工管理', 'hr_user': '员工',
}
print('%-8s %s' % ('角色', '应用权限'))
for role, keys in ROLES.items():
    apps = ' + '.join(APP_MAP.get(k, k) for k in keys if k in atom_ids)
    print('%-8s %s' % (role.replace('角色', ''), apps))
print('\n完成 ✓')
