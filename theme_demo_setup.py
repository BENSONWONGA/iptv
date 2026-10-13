#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""服务器准备 + 演示库创建：
1. 服务器从 GitHub 下载 design-themes 20.0（含直连/镜像回退）
2. 解压 12 个官方主题到 addons
3. dbfilter 放宽为 ^(benson|theme_demo)$（备份 conf）
4. 重启 Odoo
5. 创建 theme_demo 库（demo 数据 + en_US + admin/Demo@2026）
6. 在 theme_demo 安装 website_sale
"""
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
MASTER = 'Odoo20Master_Xn9pTq4R'
THEMES = ['theme_anelusia', 'theme_kea', 'theme_loftspace', 'theme_treehouse',
          'theme_graphene', 'theme_enark', 'theme_bistro', 'theme_cobalt',
          'theme_beauty', 'theme_orchid', 'theme_nano', 'theme_avantgarde']

ex = BTExec()

# ===== 1. 服务器下载源码 =====
print('===== 1. 服务器下载 design-themes =====')
out = ex.run(
    'cd /tmp && rm -f dt20.tar.gz && '
    '(timeout 300 curl -sSL -o dt20.tar.gz https://codeload.github.com/odoo/design-themes/tar.gz/refs/heads/20.0 || '
    ' timeout 300 curl -sSL -o dt20.tar.gz https://mirror.ghproxy.com/https://github.com/odoo/design-themes/archive/refs/heads/20.0.tar.gz || '
    ' timeout 300 curl -sSL -o dt20.tar.gz https://ghfast.top/https://github.com/odoo/design-themes/archive/refs/heads/20.0.tar.gz) ; '
    'ls -la dt20.tar.gz && file dt20.tar.gz | head -1 && echo DL_DONE',
    timeout=330, name='theme-prep')
print('下载:', 'OK' if 'DL_DONE' in out else out[-400:])
if 'DL_DONE' not in out or 'gzip' not in out:
    raise SystemExit('下载失败')

# ===== 2. 解压 12 个主题 =====
print('===== 2. 解压主题到 addons =====')
pats = ' '.join("--wildcards 'design-themes-20.0/%s/*'" % t for t in THEMES)
out = ex.run(
    "cd /tmp && tar -xzf dt20.tar.gz %s && ls -d design-themes-20.0/theme_*/ | wc -l && "
    "for t in %s; do rm -rf /opt/odoo20/addons/$t; mv design-themes-20.0/$t /opt/odoo20/addons/; done && "
    "chown -R odoo20:odoo20 /opt/odoo20/addons/theme_* && "
    "ls /opt/odoo20/addons/ | grep -c '^theme_' && rm -rf /tmp/design-themes-20.0 /tmp/dt20.tar.gz && echo EXTRACT_OK" % (pats, ' '.join(THEMES)),
    timeout=180, name='theme-prep')
print('解压:', 'OK' if 'EXTRACT_OK' in out else out[-400:])
if 'EXTRACT_OK' not in out:
    raise SystemExit('解压失败')

# ===== 3. dbfilter 放宽 =====
print('===== 3. 修改 dbfilter =====')
out = ex.run(
    'cp /etc/odoo20.conf /etc/odoo20.conf.bak_themedemo && '
    "sed -i 's/^dbfilter = .*/dbfilter = ^(benson|theme_demo)$/' /etc/odoo20.conf && "
    'grep dbfilter /etc/odoo20.conf && echo FILTER_OK',
    timeout=30, name='theme-prep')
print('dbfilter:', 'OK' if 'FILTER_OK' in out else out[-200:])

# ===== 4. 重启 =====
print('===== 4. 重启 Odoo =====')
ex.run('systemctl restart odoo20', timeout=90, name='theme-prep')
time.sleep(12)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=30, name='theme-prep')
print('重启:', 'OK' if 'ACTIVE_OK' in out else out[-200:])

# ===== 5. 创建 theme_demo 库 =====
print('===== 5. 创建 theme_demo 库 =====')
r = requests.post(HOST + '/web/database/create', data={
    'master_pwd': MASTER, 'name': 'theme_demo', 'lang': 'en_US',
    'password': 'Demo@2026', 'login': 'admin', 'demo': 'on'},
    timeout=900, allow_redirects=True)
print('HTTP', r.status_code, '| URL:', r.url[-60:])
ok = r.status_code == 200 and ('theme_demo' in r.url or 'web/login' in r.url or b'theme_demo' in r.content)
print('建库:', 'OK' if ok else '需检查')
if not ok:
    print(r.text[:500])

# ===== 6. theme_demo 安装 website_sale =====
print('===== 6. theme_demo 安装 website_sale =====')
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=900):
    rr = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = rr.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:400])
    return d['result']


a = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'theme_demo', 'login': 'admin', 'password': 'Demo@2026'}}, timeout=120)
print('登录 theme_demo:', a.json().get('result', {}).get('uid', 'FAIL'))
rpc('ir.module.module', 'update_list')
mods = rpc('ir.module.module', 'search_read', [[['name', '=', 'website_sale']]], {'fields': ['name', 'state']})
print('website_sale:', mods)
if mods and mods[0]['state'] != 'installed':
    rpc('ir.module.module', 'button_immediate_install', [[mods[0]['id']]])
    m2 = rpc('ir.module.module', 'search_read', [[['name', '=', 'website_sale']]], {'fields': ['state']})
    print('安装 website_sale:', m2[0]['state'])

# 验证前台可访问
time.sleep(3)
r = requests.get(HOST + '/?db=theme_demo', timeout=120)
print('前台 ?db=theme_demo: HTTP %s, 长度 %d' % (r.status_code, len(r.text)))
print('=== 准备完成，可逐主题安装截图 ===')
