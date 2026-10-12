#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 Odoo RPC 登录"""
import json
import requests

HOST = 'http://220.162.99.166:9000'
DB = 'benson'
USER = 'admin'
PASS = 'Benson@2026'

s = requests.Session()


def call(service, method, *args):
    r = s.post(HOST + '/jsonrpc', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'service': service, 'method': method, 'args': args},
    }, timeout=60)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


# 登录测试
uid = call('common', 'login', DB, USER, PASS)
print('登录成功 uid =', uid)

# 版本信息
ver = call('common', 'version')
print('Odoo 版本:', ver.get('server_version'), '| serie:', ver.get('server_serie'))

# 已安装模块数
mods = call('object', 'execute_kw', DB, uid, PASS,
            'ir.module.module', 'search_count',
            [[['state', '=', 'installed']]])
print('已安装模块数:', mods)

# 检查关键模块
mods2 = call('object', 'execute_kw', DB, uid, PASS,
             'ir.module.module', 'search_read',
             [[['name', 'in', ['sale_management', 'purchase', 'mrp', 'account',
                                'hr_attendance', 'hr_holidays', 'hr_expense', 'project']]],
              ['state']],
             {'limit': 20})
print('关键模块状态:')
for m in mods2:
    print('  ', m['id'], m.get('state'))
