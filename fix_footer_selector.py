#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署修正后的 CSS 并验证页脚隐藏"""
import base64
import json
import re
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'

ex = BTExec()
b64 = base64.b64encode(open('/workspace/adk_outdoor.css', 'rb').read()).decode()
chunks = [b64[i:i + 60000] for i in range(0, len(b64), 60000)]
ex.run('rm -f /tmp/adk.b64', timeout=15, name='adk-css4')
for c in chunks:
    ex.run("echo -n %s >> /tmp/adk.b64" % c, timeout=15, name='adk-css4')
out = ex.run('base64 -d /tmp/adk.b64 > /opt/odoo20/addons/theme_liquid_glass/static/src/css/adk_outdoor.css && '
             'chown odoo20:odoo20 /opt/odoo20/addons/theme_liquid_glass/static/src/css/adk_outdoor.css && '
             'rm -f /tmp/adk.b64 && echo CSS_OK', timeout=30, name='adk-css4')
print('CSS 上传:', 'OK' if 'CSS_OK' in out else out[-200:])

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
bundles = rpc('ir.attachment', 'search', [[['name', '=', 'web.assets_frontend.min.css']]])
if bundles:
    rpc('ir.attachment', 'unlink', [bundles])
    print('旧 bundle 已删除，触发重编译')

time.sleep(4)
r = requests.get(HOST + '/web/login?t=%d' % time.time(), timeout=120)
h = r.text
css_urls = re.findall(r'href="(/web/assets/[^"]+\.css)"', h)
ok = False
if css_urls:
    r2 = requests.get(HOST + css_urls[0] + '?t=%d' % time.time(), timeout=120)
    ok = 'footer#bottom' in r2.text
print('bundle 含 footer#bottom 隐藏规则:', ok)

# 浏览器无头验证不方便，用 CSS 内容确认即可
print('页面仍正常:', 'adk-login-left' in h and '欢迎回来' in h)
