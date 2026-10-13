#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""服务器准备 v2：git 稀疏克隆(走 ghfast 镜像) → dbfilter → 重启 → 建库 → 装 website_sale"""
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
MASTER = 'Odoo20Master_Xn9pTq4R'
THEMES = ['theme_anelusia', 'theme_kea', 'theme_loftspace', 'theme_treehouse',
          'theme_graphene', 'theme_enark', 'theme_bistro', 'theme_cobalt',
          'theme_beauty', 'theme_orchid', 'theme_nano', 'theme_avantgarde']

ex = BTExec()

# ===== 1. git 稀疏克隆（走镜像） =====
print('===== 1. git 稀疏克隆 =====')
sparse = ' '.join(THEMES)
out = ex.run(
    'which git; cd /tmp && rm -rf dt && '
    'timeout 500 git clone --depth 1 --branch 20.0 --filter=blob:none --no-checkout '
    'https://ghfast.top/https://github.com/odoo/design-themes.git dt 2>&1 | tail -2 && '
    'cd dt && git sparse-checkout init --cone && git sparse-checkout set %s && '
    'timeout 400 git checkout 2>&1 | tail -1 && ls -d theme_*/ | wc -l && du -sh . --exclude=.git && echo CLONE_OK' % sparse,
    timeout=560, name='tp2')
print('克隆:', 'OK' if 'CLONE_OK' in out else out[-500:])
if 'CLONE_OK' not in out:
    raise SystemExit('克隆失败')

# ===== 2. 移入 addons =====
print('===== 2. 移入 addons =====')
out = ex.run(
    'cd /tmp/dt && for t in %s; do rm -rf /opt/odoo20/addons/$t; mv $t /opt/odoo20/addons/; done && '
    'chown -R odoo20:odoo20 /opt/odoo20/addons/theme_anelusia /opt/odoo20/addons/theme_kea /opt/odoo20/addons/theme_loftspace /opt/odoo20/addons/theme_treehouse /opt/odoo20/addons/theme_graphene /opt/odoo20/addons/theme_enark /opt/odoo20/addons/theme_bistro /opt/odoo20/addons/theme_cobalt /opt/odoo20/addons/theme_beauty /opt/odoo20/addons/theme_orchid /opt/odoo20/addons/theme_nano /opt/odoo20/addons/theme_avantgarde && '
    'ls /opt/odoo20/addons/ | grep -cE "^theme_(anelusia|kea|loftspace|treehouse|graphene|enark|bistro|cobalt|beauty|orchid|nano|avantgarde)$" && rm -rf /tmp/dt && echo MOVE_OK' % ' '.join(THEMES),
    timeout=120, name='tp2')
print('移动:', 'OK' if 'MOVE_OK' in out else out[-300:])

# ===== 3. dbfilter =====
print('===== 3. dbfilter =====')
out = ex.run(
    "sed -i 's/^dbfilter = .*/dbfilter = ^(benson|theme_demo)$/' /etc/odoo20.conf && grep dbfilter /etc/odoo20.conf && echo FILTER_OK",
    timeout=30, name='tp2')
print('dbfilter:', 'OK' if 'FILTER_OK' in out else out[-200:])

# ===== 4. 重启 =====
print('===== 4. 重启 =====')
ex.run('systemctl restart odoo20', timeout=90, name='tp2')
time.sleep(12)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=30, name='tp2')
print('重启:', 'OK' if 'ACTIVE_OK' in out else out[-200:])

# ===== 5. 创建 theme_demo =====
print('===== 5. 创建 theme_demo =====')
r = requests.post(HOST + '/web/database/create', data={
    'master_pwd': MASTER, 'name': 'theme_demo', 'lang': 'en_US',
    'password': 'Demo@2026', 'login': 'admin', 'demo': 'on'},
    timeout=1200, allow_redirects=True)
print('HTTP', r.status_code, '| final:', r.url[:100])

# 验证登录
s = requests.Session()
a = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'theme_demo', 'login': 'admin', 'password': 'Demo@2026'}}, timeout=120)
uid = a.json().get('result', {}).get('uid')
print('theme_demo 登录:', 'OK uid=%s' % uid if uid else 'FAIL')
if not uid:
    print('建库异常, 响应片段:', r.text[:300])
    raise SystemExit(1)

# ===== 6. 安装 website_sale =====
print('===== 6. 安装 website_sale =====')


def rpc(model, method, args=None, kwargs=None, timeout=1200):
    rr = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = rr.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:400])
    return d['result']


rpc('ir.module.module', 'update_list')
mods = rpc('ir.module.module', 'search_read', [[['name', '=', 'website_sale']]], {'fields': ['name', 'state']})
if mods and mods[0]['state'] != 'installed':
    rpc('ir.module.module', 'button_immediate_install', [[mods[0]['id']]])
m2 = rpc('ir.module.module', 'search_read', [[['name', '=', 'website_sale']]], {'fields': ['state']})
print('website_sale:', m2[0]['state'] if m2 else 'missing')

# ===== 7. 验证前台 =====
time.sleep(3)
r = requests.get(HOST + '/?db=theme_demo&t=%d' % time.time(), timeout=180)
print('前台: HTTP %s 长度 %d' % (r.status_code, len(r.text)))
print('=== 准备完成 ===')
