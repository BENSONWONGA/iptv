#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核实品牌替换状态：公司名/logo/website/favicon"""
import json
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=120)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
uid = r.json()['result']['uid']
print('RPC 登录 ✓ uid=%s' % uid)

# 1. res.company
coms = rpc('res.company', 'search_read', [[['id', 'in', [1, 2, 3]]], ['id', 'name', 'logo', 'street', 'city']])
for c in coms:
    print('company %s: name=%r logo=%r' % (c['id'], c['name'], str(c['logo'])[:100]))

# 2. website
try:
    webs = rpc('website', 'search_read', [[['id', 'in', [1, 2, 3]]], ['id', 'name', 'logo', 'favicon']])
    for w in webs:
        print('website %s: name=%r logo=%r favicon=%r' % (
            w['id'], w['name'], str(w['logo'])[:100], str(w['favicon'])[:100]))
except Exception as e:
    print('website: %s' % e)

# 3. 伙伴/其他含旧公司名的记录
for model in ['res.partner', 'res.users']:
    recs = rpc(model, 'search_read', [[['name', 'ilike', 'Benson'], ['id', '!=', 1]], ['id', 'name']])
    print('%s 含 Benson: %s' % (model, recs))

# 4. 登录页实际引用的 logo
r = s.get(HOST + '/web/login', timeout=30)
html = r.text
import re
for m in re.finditer(r'(?:src|href)="([^"]*(?:logo|favicon)[^"]*)"', html):
    print('login页引用:', m.group(1))
print('登录页标题:', re.search(r'<title>(.*?)</title>', html).group(1) if '<title>' in html else '?')

# 5. 当前安装的主题模块
mods = rpc('ir.module.module', 'search_read', [[['state', '=', 'installed'], ['name', 'like', 'theme']], ['name', 'state']])
print('已装主题:', mods)

# 6. 主页 URL（登录后跳转）
info = rpc('res.users', 'read', [[uid], ['name', 'company_id', 'action_id']])
print('admin:', info)
