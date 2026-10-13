#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四轮修复：菜单zh_CN值 + header电话 + 重建CSS bundle"""
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

# ---------- 1. 菜单中文名（zh_CN 上下文写翻译值） ----------
ZH = {'lang': 'zh_CN'}
# 先看当前 zh_CN 值
m = rpc('website.menu', 'read', [[10, 4, 11]], {'fields': ['name'], 'context': ZH})
print('当前 zh_CN 名:', [(x['id'], x['name']) for x in m])
rpc('website.menu', 'write', [[10], {'name': '全部商品'}], {'context': ZH})
rpc('website.menu', 'write', [[4], {'name': '首页'}], {'context': ZH})
rpc('website.menu', 'write', [[11], {'name': '全部商品'}], {'context': ZH})
m = rpc('website.menu', 'read', [[10, 4, 11]], {'fields': ['name'], 'context': ZH})
print('修正后 zh_CN 名:', [(x['id'], x['name']) for x in m])

# ---------- 2. header 电话替换视图 ----------
key = 'adk_outdoor.header_phone_zh'
exist = rpc('ir.ui.view', 'search', [[['key', '=', key]]])
if not exist:
    base = rpc('ir.ui.view', 'search', [[['key', '=', 'website.header_text_element']]])[0]
    NEW_A = ('<a href="tel:+865958888666" class="nav-link o_nav-link_secondary p-2">\n'
             '    <i class="oi oi-1x oi-fw oi-filled me-1" data-icon="phone"/>\n'
             '    <span class="o_force_ltr">+86 595-8888 6666</span>\n'
             '</a>')
    arch = ('<data>\n' + '\n'.join(
        '<xpath expr="//a[@href=\'tel:+1 555-555-5556\']" position="replace">%s</xpath>' % NEW_A
        for _ in range(3)) + '\n</data>')
    rpc('ir.ui.view', 'create', [{
        'name': key, 'key': key, 'type': 'qweb', 'inherit_id': base, 'arch_db': arch}])
    print('header 电话视图已创建 ✓')
else:
    print('header 电话视图已存在')

# ---------- 3. 重建 CSS bundle（删除旧 bundle 附件，触发重编译） ----------
from bt_exec import BTExec
ex = BTExec()
ex.run('systemctl restart odoo20', timeout=40, name='adk-restart2')
time.sleep(10)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=30, name='adk-restart2')
print('重启:', 'OK' if 'ACTIVE_OK' in out else out[-200:])

# 删除 bundle 附件强制重编译
bundles = rpc('ir.attachment', 'search', [[['name', '=', 'web.assets_frontend.min.css']]])
if bundles:
    rpc('ir.attachment', 'unlink', [bundles])
    print('已删除 %d 个旧 bundle 附件，将自动重编译' % len(bundles))

time.sleep(2)
# ---------- 4. 验证 ----------
r = requests.get(HOST + '/?v=%d' % time.time(), timeout=60)
h = r.text
print('\n=== 验证 ===')
print('菜单 全部商品:', '全部商品' in h, '| 商店:', '商店' in h)
print('电话 +86 595:', '+86 595-8888 6666' in h, '| +1 555:', '+1 555-555-5556' in h)
# CSS bundle 检查
import re
css_urls = re.findall(r'href="(/web/assets/[^"]+\.css)"', h)
print('CSS bundles:', len(css_urls))
for u in css_urls[:1]:
    r2 = requests.get(HOST + u, timeout=60)
    c = r2.text
    print('bundle 内 #e67e22:', '#e67e22' in c, '| --btn-bg:', '--btn-bg: #e67e22' in c)
    print('important 规则:', 'background-color: #e67e22!important' in c.replace(' ', '') or
          'background-color:#e67e22!important' in c.replace(' ', ''))
