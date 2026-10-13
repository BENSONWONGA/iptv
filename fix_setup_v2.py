#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 v2 遗留：移动 12 主题 + 完整参数建库"""
import re
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
MASTER = 'Odoo20Master_Xn9pTq4R'
THEMES = ['theme_anelusia', 'theme_kea', 'theme_loftspace', 'theme_treehouse',
          'theme_graphene', 'theme_enark', 'theme_bistro', 'theme_cobalt',
          'theme_beauty', 'theme_orchid', 'theme_nano', 'theme_avantgarde']

ex = BTExec()

# ===== 1. 移动主题（逐个、带检查） =====
print('===== 1. 移动 12 个主题 =====')
moves = []
for t in THEMES:
    out = ex.run('if [ -d /opt/odoo20/addons/%(t)s ] && [ ! -d /tmp/dt/%(t)s ]; then echo ALREADY; '
                 'elif [ -d /tmp/dt/%(t)s ]; then rm -rf /opt/odoo20/addons/%(t)s; mv /tmp/dt/%(t)s /opt/odoo20/addons/ && echo MOVED; '
                 'else echo MISSING; fi' % {'t': t}, timeout=30, name='tp3')
    st = 'ALREADY' if 'ALREADY' in out else ('MOVED' if 'MOVED' in out else ('MISSING' if 'MISSING' in out else out[-100:]))
    moves.append('%s:%s' % (t, st))
print('  ' + ', '.join(moves))
out = ex.run('chown -R odoo20:odoo20 /opt/odoo20/addons/theme_anelusia /opt/odoo20/addons/theme_kea /opt/odoo20/addons/theme_loftspace /opt/odoo20/addons/theme_treehouse /opt/odoo20/addons/theme_graphene /opt/odoo20/addons/theme_enark /opt/odoo20/addons/theme_bistro /opt/odoo20/addons/theme_cobalt /opt/odoo20/addons/theme_beauty /opt/odoo20/addons/theme_orchid /opt/odoo20/addons/theme_nano /opt/odoo20/addons/theme_avantgarde 2>/dev/null; ls /opt/odoo20/addons/ | grep -cE "^theme_(anelusia|kea|loftspace|treehouse|graphene|enark|bistro|cobalt|beauty|orchid|nano|avantgarde)$"', timeout=60, name='tp3')
print('addons 中就位:', out.strip().splitlines()[-1] if out.strip() else '?', '/ 12')

# ===== 2. 重启（让 odoo 识别新模块） =====
print('===== 2. 重启 =====')
ex.run('systemctl restart odoo20', timeout=90, name='tp3')
time.sleep(12)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=30, name='tp3')
print('重启:', 'OK' if 'ACTIVE_OK' in out else out[-150:])

# ===== 3. 建库（完整参数） =====
print('===== 3. 创建 theme_demo =====')
for attempt, extra in enumerate([
        {'demo': 'on', 'country_code': 'CN', 'phone': ''},
        {'demo': 'true', 'country_code': 'CN', 'phone': ''},
        {'country_code': 'CN', 'phone': ''}]):
    data = {'master_pwd': MASTER, 'name': 'theme_demo', 'lang': 'en_US',
            'password': 'Demo@2026', 'login': 'admin'}
    data.update(extra)
    r = requests.post(HOST + '/web/database/create', data=data, timeout=1200, allow_redirects=False)
    print('尝试 %d: HTTP %s | Location: %s' % (attempt + 1, r.status_code, r.headers.get('Location', '-')[:80]))
    if r.status_code in (301, 302, 303):
        loc = r.headers.get('Location', '')
        if 'select' in loc or 'manager' in loc or 'login' in loc:
            print('  → 可能成功（重定向）')
            break
    if r.status_code == 200:
        # 看响应里有没有报错信息
        errs = re.findall(r'(?:alert|danger)[^>]*>([^<]{5,120})', r.text)
        print('  页面提示:', errs[:3])
    # 验证
    s = requests.Session()
    a = s.post(HOST + '/web/session/authenticate', json={
        'jsonrpc': '2.0', 'params': {'db': 'theme_demo', 'login': 'admin', 'password': 'Demo@2026'}}, timeout=120)
    if a.json().get('result', {}).get('uid'):
        print('theme_demo 已可用!')
        break
    else:
        print('  仍未可用，%s' % ('换参数重试' if attempt < 2 else '放弃'))
