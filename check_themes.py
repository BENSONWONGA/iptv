#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查服务器上可用/已安装的主题模块与 Odoo 版本信息"""
import json

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
ex = BTExec()

# 1. 服务器上已有的主题模块目录 + addons 路径 + 启动参数
out = ex.run('ls -d /opt/odoo20/addons/theme* /opt/odoo20/*/addons/theme* 2>/dev/null; echo ---ADDONS_PATH---; '
             'systemctl cat odoo20 2>/dev/null | grep -E "ExecStart"; echo ---ENTERPRISE---; '
             'ls -d /opt/odoo20/addons/web_enterprise /opt/odoo20/enterprise 2>/dev/null || echo no_enterprise_dir; echo ---VER---; '
             'grep -m1 "\\"version\\"\\|version:" /opt/odoo20/addons/web/__manifest__.py 2>/dev/null',
             timeout=40, name='theme-check')
print(out)
print('=' * 50)

# 2. RPC: 数据库中的主题模块 + 企业版判断
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=300):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

mods = rpc('ir.module.module', 'search_read', [[['name', 'like', 'theme_']]],
           {'fields': ['name', 'state', 'latest_version']})
print('数据库中的主题模块:')
for m in mods:
    print('  %-32s %-12s %s' % (m['name'], m['state'], m.get('latest_version', '')))

ent = rpc('ir.module.module', 'search_read', [[['name', 'in', ['web_enterprise']]]],
          {'fields': ['name', 'state']})
print('企业版模块:', ent or '不存在(社区版)')
ver = rpc('ir.module.module', 'search_read', [[['name', '=', 'web']]],
          {'fields': ['name', 'latest_version']})
print('web 模块版本:', ver)
