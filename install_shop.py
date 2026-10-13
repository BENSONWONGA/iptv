#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安装 website_sale(电商) + theme_default(网站模板)"""
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'

s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=900):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}},
    }, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']
print('RPC 登录 ✓ uid=%s' % uid)

rpc('ir.module.module', 'update_list')
print('模块列表已更新')


def install_module(name, timeout=900):
    ids = rpc('ir.module.module', 'search', [[['name', '=', name]]])
    if not ids:
        print('!! 未找到模块 %s' % name)
        return False
    st = rpc('ir.module.module', 'read', [ids], {'fields': ['state']})[0]['state']
    if st == 'installed':
        print('%s 已安装 ✓' % name)
        return True
    print('安装 %s 中(state=%s)...' % (name, st))
    rpc('ir.module.module', 'button_immediate_install', [ids], timeout=timeout)
    st = rpc('ir.module.module', 'read', [ids], {'fields': ['state']})[0]['state']
    print('%s 安装后状态: %s' % (name, st))
    return st == 'installed'


# 1. 电商模块
ok1 = install_module('website_sale', timeout=1200)
# 2. 网站模板
ok2 = install_module('theme_default', timeout=1200)

print('\n=== 安装结果: website_sale=%s theme_default=%s ===' % (ok1, ok2))

# 3. 验证
mods = rpc('ir.module.module', 'search_read', [[['name', 'in', ['website_sale', 'theme_default']]]],
           {'fields': ['name', 'state']})
print(mods)
shop_menu = rpc('website.menu', 'search_read', [[['url', 'like', '/shop']]],
                {'fields': ['name', 'url']})
print('商店菜单:', shop_menu)
