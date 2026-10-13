#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安装 theme_boec 前的勘察：addons 目录、数据库大小、网站页面、自定义视图清单"""
import json

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
ex = BTExec()

# 服务器勘察
out = ex.run(
    'ls /opt/odoo20/addons/ | head -60; echo ---DB_SIZE---; '
    'sudo -u postgres psql -l 2>/dev/null | grep benson || psql -U postgres -l 2>/dev/null | grep benson; echo ---PG_OK---; '
    'which pg_dump; echo ---DISK---; df -h /opt | tail -1',
    timeout=40, name='boec-recon')
print(out)
print('=' * 60)

s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=300):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

# 网站与首页
sites = rpc('website', 'search_read', [[]], {'fields': ['name', 'homepage_url', 'domain']})
print('网站:', json.dumps(sites, ensure_ascii=False))

# 我们的定制视图（登录页改造、首页等）
views = rpc('ir.ui.view', 'search_read', [[['key', 'ilike', 'adk'], '|', ['name', 'ilike', 'ADK'], '|',
                                          ['key', 'ilike', 'x_'], ['name', 'ilike', '奥登科']]],
            {'fields': ['name', 'key', 'model', 'website_id'], 'limit': 50})
print('定制视图(%d):' % len(views))
for v in views:
    print('  id=%s key=%s model=%s' % (v['id'], v.get('key'), v.get('model')))

# 首页 view
hp = rpc('ir.ui.view', 'search_read', [[['key', '=', 'website.homepage']]],
         {'fields': ['id', 'key', 'name', 'arch_db']})
print('首页视图:', [(h['id'], h['key']) for h in hp], 'arch 长度:', [len(h.get('arch_db') or '') for h in hp])

# 已安装的网站相关模块
mods = rpc('ir.module.module', 'search_read', [[['state', '=', 'installed'], ['name', 'in',
           ['website', 'website_sale', 'website_blog', 'sale_management', 'website_sale_wishlist']]]],
           {'fields': ['name', 'latest_version']})
print('网站相关模块:', json.dumps(mods, ensure_ascii=False))

# theme_boec 是否已存在
boec = rpc('ir.module.module', 'search_read', [[['name', '=', 'theme_boec']]],
           {'fields': ['name', 'state']})
print('theme_boec 模块状态:', boec or '服务器上不存在，需上传')
