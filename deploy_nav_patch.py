#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署导航栏/讨论侧栏浅色补丁 → 重启 → 清bundle → 验证"""
import base64
import json
import re
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
NAVBAR = '/opt/odoo20/addons/theme_liquid_glass/static/src/scss/navbar.scss'

ex = BTExec()

# 1. 上传补丁并追加到 navbar.scss 末尾
b64 = base64.b64encode(open('/workspace/nav_light_patch.scss', 'rb').read()).decode()
chunks = [b64[i:i + 60000] for i in range(0, len(b64), 60000)]
ex.run('rm -f /tmp/nav.b64', timeout=15, name='nav-patch')
for c in chunks:
    ex.run("echo -n %s >> /tmp/nav.b64" % c, timeout=15, name='nav-patch')
out = ex.run('base64 -d /tmp/nav.b64 > /tmp/nav_patch.scss && '
             'cat /tmp/nav_patch.scss >> %s && rm -f /tmp/nav.b64 /tmp/nav_patch.scss && '
             'chown odoo20:odoo20 %s && echo PATCH_OK' % (NAVBAR, NAVBAR),
             timeout=30, name='nav-patch')
print('补丁追加:', 'OK' if 'PATCH_OK' in out else out[-300:])

# 2. 重启
ex.run('systemctl restart odoo20', timeout=40, name='nav-patch')
time.sleep(12)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=30, name='nav-patch')
print('重启:', 'OK' if 'ACTIVE_OK' in out else out[-200:])

# 3. 清后端 bundle
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
atts = rpc('ir.attachment', 'search_read', [[['name', 'like', 'web.assets_']]],
           {'fields': ['name']})
to_del = [a['id'] for a in atts if a['name'].endswith(('.min.css', '.min.js')) and 'frontend' not in a['name']]
if to_del:
    rpc('ir.attachment', 'unlink', [to_del])
    print('已删除 %d 个后端 bundle 附件: %s' % (len(to_del), [a['name'] for a in atts if a['id'] in to_del][:6]))

# 4. 验证编译
time.sleep(4)
r = s.get(HOST + '/odoo?t=%d' % time.time(), timeout=120)
css_urls = re.findall(r'href="(/web/assets/[^"]+\.css)"', r.text)
main_css = [u for u in css_urls if 'assets_web.min.css' in u or 'assets_backend' in u]
print('bundle:', main_css[:1])
if main_css:
    r2 = s.get(HOST + main_css[0] + '?t=%d' % time.time(), timeout=120)
    c = r2.text
    for k, v in {
        '--NavBar-entry-color 覆盖': '--NavBar-entry-color: #2d3a4a' in c or '--NavBar-entry-color:#2d3a4a' in c,
        'o_menu_brand 深灰规则': '.o_menu_brand' in c and '#2d3a4a' in c,
        'MessagingMenu-tab active 青绿': 'MessagingMenu-tab' in c and '#06bea0' in c,
        'tabIcon 药丸白字': 'MessagingMenu-tabIcon' in c,
    }.items():
        print('  %-28s %s' % (k, '✓' if v else '✗'))
print('=== 补丁部署完成 ===')
