#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""上传登录页 CSS + 验证"""
import base64
import re
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'

# 1. 上传 CSS
ex = BTExec()
b64 = base64.b64encode(open('/workspace/adk_outdoor.css', 'rb').read()).decode()
chunks = [b64[i:i + 60000] for i in range(0, len(b64), 60000)]
ex.run('rm -f /tmp/adk.b64', timeout=15, name='adk-css3')
for c in chunks:
    ex.run("echo -n %s >> /tmp/adk.b64" % c, timeout=15, name='adk-css3')
out = ex.run('base64 -d /tmp/adk.b64 > /opt/odoo20/addons/theme_liquid_glass/static/src/css/adk_outdoor.css && '
             'chown odoo20:odoo20 /opt/odoo20/addons/theme_liquid_glass/static/src/css/adk_outdoor.css && '
             'rm -f /tmp/adk.b64 && echo CSS_OK', timeout=30, name='adk-css3')
print('CSS 上传:', 'OK' if 'CSS_OK' in out else out[-200:])

# 2. 删除旧 bundle 触发重编译
import json
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
    print('旧 bundle 已删除(%d)，自动重编译' % len(bundles))

# 3. 验证登录页
time.sleep(3)
r = requests.get(HOST + '/web/login', timeout=60)
h = r.text
print('\n=== 登录页验证 ===')
print('HTTP:', r.status_code)
checks = {
    '左面板 adk-login-left': 'adk-login-left' in h,
    '右面板 adk-login-right': 'adk-login-right' in h,
    '标题 欢迎回来': '欢迎回来' in h,
    '标语 山野之履': '山野之履' in h,
    '返回官网链接': '返回官网' in h,
    '登录表单': 'oe_login_form' in h,
    '重置密码': '重置密码' in h,
    '登录按钮': '>登录</button>' in h or '登录</button>' in h,
}
for k, v in checks.items():
    print('  %-18s %s' % (k, '✓' if v else '✗'))
# CSS bundle 含登录样式
css_urls = re.findall(r'href="(/web/assets/[^"]+\.css)"', h)
if css_urls:
    r2 = requests.get(HOST + css_urls[0], timeout=60)
    c = r2.text
    print('bundle 含 .adk-login-left:', '.adk-login-left' in c)
    print('bundle 含 o_web_login:', 'o_web_login' in c)
else:
    print('!! 未找到 CSS bundle')
