#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完成主题 checkout + 移动 + theme_demo 装 website_sale"""
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
THEMES = ['theme_anelusia', 'theme_kea', 'theme_loftspace', 'theme_treehouse',
          'theme_graphene', 'theme_enark', 'theme_bistro', 'theme_cobalt',
          'theme_beauty', 'theme_orchid', 'theme_nano', 'theme_avantgarde']

ex = BTExec()

# ===== 1. 重新 checkout（blob:none 克隆需下载文件内容） =====
print('===== 1. git checkout（下载文件内容） =====')
out = ex.run('cd /tmp/dt && timeout 560 git checkout 2>&1 | tail -2; ls -d theme_*/ 2>/dev/null | wc -l; du -sh --exclude=.git . ; echo CO_END',
             timeout=580, name='co')
n = 0
for ln in out.splitlines():
    ln = ln.strip()
    if ln.isdigit():
        n = int(ln)
print('检出主题数: %d/12' % n)
print(out[-300:])
if n < 12:
    raise SystemExit('检出不全')

# ===== 2. 移动 + 权限 =====
print('===== 2. 移动到 addons =====')
outs = []
for t in THEMES:
    out = ex.run('mv /tmp/dt/%(t)s /opt/odoo20/addons/ && echo M_OK' % {'t': t}, timeout=30, name='mv')
    outs.append('OK' if 'M_OK' in out else 'F')
print('移动:', outs)
out = ex.run('chown -R odoo20:odoo20 ' + ' '.join('/opt/odoo20/addons/' + t for t in THEMES) + ' && '
             'ls /opt/odoo20/addons/ | grep -cE "^theme_(anelusia|kea|loftspace|treehouse|graphene|enark|bistro|cobalt|beauty|orchid|nano|avantgarde)$" && rm -rf /tmp/dt && echo ALL_OK',
             timeout=90, name='mv')
print('就位:', 'OK' if 'ALL_OK' in out else out[-200:])

# ===== 3. 重启 =====
print('===== 3. 重启 =====')
ex.run('systemctl restart odoo20', timeout=90, name='co')
time.sleep(12)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=30, name='co')
print('重启:', 'OK' if 'ACTIVE_OK' in out else out[-150:])

# ===== 4. theme_demo 安装 website_sale =====
print('===== 4. theme_demo 安装 website_sale =====')
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=1200):
    rr = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = rr.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:300])
    return d['result']


a = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'theme_demo', 'login': 'admin', 'password': 'Demo@2026'}}, timeout=120)
print('登录:', 'OK' if a.json().get('result', {}).get('uid') else 'FAIL')
rpc('ir.module.module', 'update_list')
mods = rpc('ir.module.module', 'search_read',
           [[['name', 'in', ['website_sale'] + THEMES]]], {'fields': ['name', 'state']})
found = {m['name']: m['state'] for m in mods}
print('识别: %d 个, 状态样例: %s' % (len(found), dict(list(found.items())[:4])))
if found.get('website_sale') != 'installed':
    rpc('ir.module.module', 'button_immediate_install', [[m['id'] for m in mods if m['name'] == 'website_sale'][0]])
    print('website_sale 安装完成')

# ===== 5. 前台验证 =====
time.sleep(3)
r = requests.get(HOST + '/?db=theme_demo&t=%d' % time.time(), timeout=180)
print('前台: HTTP %s 长度 %d' % (r.status_code, len(r.text)))
print('=== 全部就绪 ===')
