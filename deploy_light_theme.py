#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署灰白浅色主题：备份 → 替换变量 → sed 转换 → 重启 → 清 bundle → 验证"""
import base64
import json
import re
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
SCSS_DIR = '/opt/odoo20/addons/theme_liquid_glass/static/src/scss'

ex = BTExec()

# ---------- 1. 备份当前深色主题 ----------
out = ex.run('mkdir -p /opt/odoo20/addons/theme_liquid_glass/backup_dark && '
             'cp %s/*.scss /opt/odoo20/addons/theme_liquid_glass/backup_dark/ && ls /opt/odoo20/addons/theme_liquid_glass/backup_dark/ && echo BAK_OK' % SCSS_DIR,
             timeout=30, name='light-deploy')
print('备份:', 'OK' if 'BAK_OK' in out else out[-300:])


def upload(local, remote, name):
    b64 = base64.b64encode(open(local, 'rb').read()).decode()
    chunks = [b64[i:i + 60000] for i in range(0, len(b64), 60000)]
    ex.run('rm -f /tmp/lt.b64', timeout=15, name=name)
    for c in chunks:
        ex.run("echo -n %s >> /tmp/lt.b64" % c, timeout=15, name=name)
    out = ex.run('base64 -d /tmp/lt.b64 > %s && chown odoo20:odoo20 %s && rm -f /tmp/lt.b64 && echo UP_OK' % (remote, remote),
                 timeout=30, name=name)
    return 'UP_OK' in out, out[-200:]


# ---------- 2. 上传新变量 + sed 脚本 ----------
ok, err = upload('/workspace/variables_light.scss', SCSS_DIR + '/variables.scss', 'light-deploy')
print('variables.scss 上传:', 'OK' if ok else err)
ok, err = upload('/workspace/light_sed.sh', '/tmp/light_sed.sh', 'light-deploy')
print('sed 脚本上传:', 'OK' if ok else err)

# ---------- 3. 执行转换 ----------
out = ex.run('bash /tmp/light_sed.sh && rm -f /tmp/light_sed.sh', timeout=60, name='light-deploy')
print('sed 执行:', 'OK' if 'LIGHT_SED_OK' in out else out[-400:])

# 抽查结果
out = ex.run("grep -c 'rgba(255, 255, 255' %s/glass_theme.scss %s/modals.scss; "
             "grep -n 'bg-img' %s/*.scss | grep -v backup | head -3; "
             "grep -n 'text-white: \\|2d3a4a' %s/variables.scss | head -2; echo CHECK_DONE" % (SCSS_DIR, SCSS_DIR, SCSS_DIR, SCSS_DIR),
             timeout=30, name='light-deploy')
print('转换后抽查:\n', out[:1200])

# ---------- 4. 重启 + 清 bundle ----------
ex.run('systemctl restart odoo20', timeout=40, name='light-deploy')
time.sleep(12)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=30, name='light-deploy')
print('重启:', 'OK' if 'ACTIVE_OK' in out else out[-200:])

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
bundles = rpc('ir.attachment', 'search', [[['name', 'in', [
    'web.assets_backend.min.css', 'web.assets_backend.min.js', 'web.assets_backend_lazy.min.js']]]])
if bundles:
    rpc('ir.attachment', 'unlink', [bundles])
    print('已删除 %d 个后端 bundle 附件，触发重编译' % len(bundles))

# ---------- 5. 验证编译产物 ----------
time.sleep(4)
r = s.get(HOST + '/odoo?t=%d' % time.time(), timeout=120)
h = r.text
print('\n=== webclient 访问:', r.status_code, '===')
css_urls = re.findall(r'href="(/web/assets/[^"]+\.css)"', h)
print('CSS bundle:', css_urls[:2])
if css_urls:
    r2 = s.get(HOST + css_urls[0] + '?t=%d' % time.time(), timeout=120)
    c = r2.text
    checks = {
        '浅灰渐变背景 #f5f6f8': '#f5f6f8' in c,
        'bg-img.svg 已移除': 'bg-img.svg' not in c,
        '白色玻璃 0.65': re.search(r'rgba\(255,\s?255,\s?255,\s?\.?0?\.?65\)|rgba\(255,255,255,.65\)|rgba(255, 255, 255, 0.65)', c) is not None,
        '深灰文字 #2d3a4a': '#2d3a4a' in c,
        '深色底 rgba(10,16,28) 已移除': 'rgba(10,16,28' not in c and 'rgba(10, 16, 28' not in c,
        '列表表头深底 rgba(8,16,30) 已移除': 'rgba(8,16,30' not in c and 'rgba(8, 16, 30' not in c,
    }
    for k, v in checks.items():
        print('  %-30s %s' % (k, '✓' if v else '✗'))
print('=== 部署完成 ===')
