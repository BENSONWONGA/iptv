#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""去掉报价单空状态的视频卡片：替换 sale_action_helper.xml → 重启 → 验证"""
import base64
import time

import requests
from bt_exec import BTExec

TARGET = '/opt/odoo20/addons/sale/static/src/js/sale_action_helper/sale_action_helper.xml'
SRC = '/tmp/sale_action_helper_patched.xml'

ex = BTExec()
b64 = base64.b64encode(open(SRC, 'rb').read()).decode()

cmd = (
    "echo -n %s | base64 -d > /tmp/sah_new.xml && "
    "cp %s %s.bak && "
    "cp /tmp/sah_new.xml %s && "
    "chown odoo20:odoo20 %s %s.bak && "
    "grep -c 'SaleActionHelper' %s && echo PATCH_OK"
) % (b64, TARGET, TARGET, TARGET, TARGET, TARGET, TARGET)
out = ex.run(cmd, timeout=40)
print(out[out.find('XMK'):] if 'XMK' in out else out)
assert 'PATCH_OK' in out, '写入失败'
print('sale_action_helper.xml 已替换 ✓（原文件备份 .bak）')

# 重启（静态资源包按校验和自动重建）
ex.run('systemctl restart odoo20', timeout=30)
time.sleep(9)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=20)
assert 'ACTIVE_OK' in out, out
print('Odoo 重启 ✓')

# 验证：新编译的 JS bundle 中不应再有视频缩略图引用
HOST = 'http://220.162.99.166:9000'
s = requests.Session()
s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)

import re
r = s.get(HOST + '/odoo/sales', timeout=120)
js_urls = set(re.findall(r'(/web/assets/[^"\']+\.js)', r.text))
print('JS bundle 数: %d' % len(js_urls))
found_thumb = found_open = False
for u in js_urls:
    js = s.get(HOST + u, timeout=120).text
    if 'sales_quotation_thumbnail' in js:
        found_thumb = True
    if 'openVideoPreview' in js:
        found_open = True
print('bundle 含视频缩略图: %s | 含播放方法: %s' % (found_thumb, found_open))
assert not found_thumb, '缩略图仍在 bundle 中，资产未重建'
print('视频卡片已从编译产物移除 ✓')
