#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安装并激活中文语言包"""
import json
import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'

s = requests.Session()


def call_kw(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}},
    }, timeout=600)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']

# 当前语言
langs = call_kw('res.lang', 'search_read', [[]], {'fields': ['code', 'name', 'active']})
print('现有语言:', [(l['code'], l['active']) for l in langs])

zh = [l for l in langs if l['code'].startswith('zh_CN')]
if not zh:
    # 安装中文
    wiz = call_kw('base.language.install', 'create', [{'lang_ids': [(4, call_kw(
        'res.lang', 'search', [[['code', '=', 'zh_CN']]])[0] if call_kw(
        'res.lang', 'search', [[['code', '=', 'zh_CN']]]) else False)]}])
    print('wizard:', wiz)
else:
    if not zh[0]['active']:
        call_kw('res.lang', 'write', [[zh[0]['id']], {'active': True}])
        print('已激活 zh_CN')

# 切换 admin 用户语言
call_kw('res.users', 'write', [[uid], {'lang': 'zh_CN'}])
print('admin 语言已切换为 zh_CN')

# 验证
me = call_kw('res.users', 'read', [[uid]], {'fields': ['lang', 'name']})
print('当前用户:', me)

menus = call_kw('ir.ui.menu', 'search_read',
                [[['parent_id', '=', False]]], {'fields': ['name'], 'limit': 100})
names = [m['name'] for m in menus]
print('顶级菜单(中文):', names)
