#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""替换主题：卸载 shoe_theme → 部署 theme_liquid_glass → 安装"""
import base64
import os
import time
import zipfile

SRC = '/workspace/.uploads/0221a4be-f95c-4707-8955-79223be1db43_theme_liquid_glass-20.0.1.0.0.zip'
SLIM = '/workspace/theme_liquid_glass_slim.zip'

# 1. 精简打包（剥离 description 大图，仅保留 icon.png）
if os.path.exists(SLIM):
    os.remove(SLIM)
src = zipfile.ZipFile(SRC)
total_src = sum(i.file_size for i in src.infolist())
with zipfile.ZipFile(SLIM, 'w', zipfile.ZIP_DEFLATED) as out:
    for info in src.infolist():
        n = info.filename
        # 跳过 description 下的大图/商店页（保留 icon.png）
        if 'static/description/' in n and not n.endswith('icon.png'):
            continue
        out.writestr(n, src.read(n))
print('原包 %.1f MB → 精简包 %.1f MB' % (total_src / 1e6, os.path.getsize(SLIM) / 1e6))

# 2. RPC：先卸载 shoe_theme（避免两套主题 CSS 叠加冲突）
import json
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=600)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
uid = r.json()['result']['uid']
print('RPC 登录 ✓ uid=%s' % uid)

ids = rpc('ir.module.module', 'search', [[['name', '=', 'shoe_theme']]])
if ids:
    rpc('ir.module.module', 'button_immediate_uninstall', [ids])
    print('shoe_theme 已卸载 ✓')

# 3. 上传新主题
from bt_exec import BTExec

ex = BTExec()
b64 = base64.b64encode(open(SLIM, 'rb').read()).decode()
CHUNK = 60000
chunks = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
print('分 %d 块上传...' % len(chunks))
ex.run('rm -f /tmp/lg.b64', timeout=15, name='lg-deploy')
for i, c in enumerate(chunks):
    out = ex.run("echo -n %s >> /tmp/lg.b64" % c, timeout=15, name='lg-deploy')
    if i % 50 == 0:
        print('  块 %d/%d' % (i + 1, len(chunks)))

out = ex.run('base64 -d /tmp/lg.b64 > /tmp/lg.zip && cd /opt/odoo20/addons && unzip -oq /tmp/lg.zip && '
             'chown -R odoo20:odoo20 /opt/odoo20/addons/theme_liquid_glass && '
             'rm -f /tmp/lg.b64 /tmp/lg.zip && ls /opt/odoo20/addons/theme_liquid_glass/ && echo UP_OK',
             timeout=30, name='lg-deploy')
assert 'UP_OK' in out, out
print('上传解压 ✓')

# 4. 重启 + 更新模块列表 + 安装
ex.run('systemctl restart odoo20', timeout=30, name='lg-deploy')
time.sleep(9)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=20, name='lg-deploy')
print('Odoo 重启 ✓' if 'ACTIVE_OK' in out else out)

rpc('ir.module.module', 'update_list')
ids = rpc('ir.module.module', 'search', [[['name', '=', 'theme_liquid_glass']]])
if not ids:
    raise SystemExit('未找到 theme_liquid_glass!')
mod = rpc('ir.module.module', 'read', [ids], {'fields': ['state']})
print('新主题状态:', mod[0]['state'])
if mod[0]['state'] != 'installed':
    rpc('ir.module.module', 'button_immediate_install', [ids])
    st = rpc('ir.module.module', 'read', [ids], {'fields': ['state']})[0]['state']
    print('安装后状态:', st)
    assert st == 'installed'

# 5. 验证样式文件可访问
for p in ['/theme_liquid_glass/static/src/scss/glass_theme.scss',
          '/theme_liquid_glass/static/src/js/navbar_sidebar.js',
          '/theme_liquid_glass/static/description/icon.png']:
    r = s.get(HOST + p, timeout=30)
    print('%s => %s (%d 字节)' % (p.split('/')[-1], r.status_code, len(r.content)))

# 6. 确认旧主题菜单已移除、新主题生效
menus = rpc('ir.ui.menu', 'search_read', [[['parent_id', '=', False]]],
            {'fields': ['name'], 'limit': 100, 'context': {'lang': 'zh_CN'}})
names = [m['name'] for m in menus]
print('驾驶舱菜单已移除:', '驾驶舱' not in names)
print('=== 主题替换完成 ===')
