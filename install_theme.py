#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RPC 安装 shoe_theme 模块"""
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'

s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}},
    }, timeout=900)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']
print('uid:', uid)

# 1. 更新模块列表
rpc('ir.module.module', 'update_list')
print('模块列表已更新')

# 2. 找到 shoe_theme
ids = rpc('ir.module.module', 'search', [[['name', '=', 'shoe_theme']]])
if not ids:
    raise SystemExit('未找到 shoe_theme 模块!')
mod = rpc('ir.module.module', 'read', [ids], {'fields': ['name', 'state']})
print('模块状态:', mod)

if mod[0]['state'] != 'installed':
    print('安装中...')
    rpc('ir.module.module', 'button_immediate_install', [ids])
    time.sleep(2)
    mod = rpc('ir.module.module', 'read', [ids], {'fields': ['state']})
    print('安装后状态:', mod)

# 3. 验证菜单与动作
menus = rpc('ir.ui.menu', 'search_read', [[['name', '=', '驾驶舱']]],
            {'fields': ['name', 'parent_id'], 'context': {'lang': 'zh_CN'}})
print('驾驶舱菜单:', menus)

# 4. 验证数据源
data = rpc('shoe.dashboard', 'get_dashboard_data', [])
print('KPI 数量:', len(data['kpis']))
for k in data['kpis']:
    print('  %s: %s %s' % (k['label'], k['value'], k.get('badge', '')))
print('快捷入口:', [sc['label'] for sc in data['shortcuts']])
print('月度销售:', [(m['label'], m['short']) for m in data['months']])
print('最新订单数:', len(data['orders']))

# 5. 验证静态资源可访问
for path in ['/shoe_theme/static/src/css/glass_theme.css',
             '/shoe_theme/static/src/css/dashboard.css',
             '/shoe_theme/static/src/js/dashboard.js',
             '/shoe_theme/static/src/xml/dashboard.xml',
             '/shoe_theme/static/description/icon.png']:
    r = s.get(HOST + path, timeout=30)
    print('%s => %s (%d 字节)' % (path.split('/')[-1], r.status_code, len(r.content)))

print('=== 安装验证完成 ===')
