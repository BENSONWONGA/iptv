#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 theme_demo 准备结果"""
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
ex = BTExec()

out = ex.run(
    'ls -d /opt/odoo20/addons/theme_*/ | wc -l; ls /opt/odoo20/addons/ | grep -E "^theme_(anelusia|kea|loftspace|treehouse|graphene|enark|bistro|cobalt|beauty|orchid|nano|avantgarde)$" | wc -l; '
    'grep dbfilter /etc/odoo20.conf; systemctl is-active odoo20; '
    'sudo -u postgres psql -lt 2>/dev/null | grep -E "theme_demo|benson" || psql -U odoo20 -d postgres -c "\\l" 2>/dev/null | grep -E "theme_demo|benson"',
    timeout=60, name='verify')
print(out)
print('=' * 50)
s = requests.Session()
a = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'theme_demo', 'login': 'admin', 'password': 'Demo@2026'}}, timeout=120)
uid = a.json().get('result', {}).get('uid')
print('theme_demo 登录:', 'OK uid=%s' % uid if uid else 'FAIL')
if uid:
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': 'ir.module.module', 'method': 'search_read',
                   'args': [[['name', 'in', ['website_sale', 'website']]]],
                   'kwargs': {'fields': ['name', 'state']}}}, timeout=300)
    print('模块:', r.json()['result'])
r = requests.get(HOST + '/?db=theme_demo&t=%d' % time.time(), timeout=180)
print('前台: HTTP %s 长度 %d 含theme标识:%s' % (
    r.status_code, len(r.text), 'theme_demo' in r.url or 'website' in r.text[:3000].lower()))
