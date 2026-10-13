#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终修复：货币CNY + 静态图片部署 + 首页URL替换 + CSS目录修复"""
import base64
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
print('登录 ✓')

# ========== 1. 激活 CNY 并切换公司货币（无业务数据，安全） ==========
cny_ids = rpc('res.currency', 'search', [[['name', 'in', ['CNY', 'RMB']]]],
              {'context': {'active_test': False}})
if not cny_ids:
    raise SystemExit('数据库中无 CNY 货币记录!')
rpc('res.currency', 'write', [cny_ids, {'active': True}])
cny = rpc('res.currency', 'read', [cny_ids], {'fields': ['name', 'symbol', 'rate', 'active']})[0]
print('CNY 已激活:', cny)
rpc('res.company', 'write', [[1], {'currency_id': cny_ids[0]}])
print('公司货币已切换为 CNY ✓')

# ========== 2. 部署静态资源（图片 + CSS） ==========
from bt_exec import BTExec
ex = BTExec()

FILES = [
    ('/workspace/site_assets/hero_mountain.jpg', '/opt/odoo20/addons/theme_liquid_glass/static/src/img/adk_hero.jpg'),
    ('/workspace/site_assets/brand_story.jpg', '/opt/odoo20/addons/theme_liquid_glass/static/src/img/adk_brand.jpg'),
    ('/workspace/adk_outdoor.css', '/opt/odoo20/addons/theme_liquid_glass/static/src/css/adk_outdoor.css'),
]
ex.run('mkdir -p /opt/odoo20/addons/theme_liquid_glass/static/src/img '
       '/opt/odoo20/addons/theme_liquid_glass/static/src/css && echo DIR_OK', timeout=20, name='adk-res')
for local, remote in FILES:
    b64 = base64.b64encode(open(local, 'rb').read()).decode()
    chunks = [b64[i:i + 60000] for i in range(0, len(b64), 60000)]
    ex.run('rm -f /tmp/adk.b64', timeout=15, name='adk-res')
    for c in chunks:
        ex.run("echo -n %s >> /tmp/adk.b64" % c, timeout=15, name='adk-res')
    out = ex.run('base64 -d /tmp/adk.b64 > %s && chown odoo20:odoo20 %s && rm -f /tmp/adk.b64 && echo FILE_OK' % (remote, remote),
                 timeout=30, name='adk-res')
    print(remote.split('/')[-1], '=>', 'OK' if 'FILE_OK' in out else out[-150:])

# ========== 3. 更新首页 view 中的图片 URL ==========
view = rpc('ir.ui.view', 'read', [[3001]], {'fields': ['arch_db']})[0]
arch = view['arch_db']
arch = arch.replace('/web/image/1618', '/theme_liquid_glass/static/src/img/adk_hero.jpg')
arch = arch.replace('/web/image/1619', '/theme_liquid_glass/static/src/img/adk_brand.jpg')
rpc('ir.ui.view', 'write', [[3001], {'arch_db': arch}])
print('首页图片 URL 已替换 ✓')

# 删除无效附件
rpc('ir.attachment', 'unlink', [[1618, 1619]])
print('无效附件已删除')

print('\n=== 修复完成 ===')
