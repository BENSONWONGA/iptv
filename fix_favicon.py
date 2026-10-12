#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""favicon 替换：新 logo → 多尺寸 ICO → 直写 ir.attachment 148"""
import base64
import io

import requests
from PIL import Image

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=120)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:400])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
print('uid =', r.json()['result']['uid'])

# 1. 生成 ICO：新 logo 裁边 → 256 方形画布 → 多尺寸 ico
img = Image.open('/workspace/.uploads/31c555f2-339a-4f75-b82b-03028e55105b_奥登科logops.png').convert('RGBA')
bbox = img.getbbox()
trimmed = img.crop(bbox)
w, h = trimmed.size
canvas = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
scale = min(256 / w, 256 / h)
nw, nh = int(w * scale), int(h * scale)
canvas.paste(trimmed.resize((nw, nh), Image.LANCZOS), ((256 - nw) // 2, (256 - nh) // 2), trimmed.resize((nw, nh), Image.LANCZOS))
buf = io.BytesIO()
canvas.save(buf, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
ico_b64 = base64.b64encode(buf.getvalue()).decode()
print('ICO 生成 ✓ %d bytes' % len(buf.getvalue()))

# 2. 直写附件
rpc('ir.attachment', 'write', [[148], {
    'datas': ico_b64,
    'mimetype': 'image/vnd.microsoft.icon',
    'name': 'favicon.ico',
}])
print('ir.attachment 148 已更新 ✓')

# 3. 验证：直接拉 /web/image/website/1/favicon
r = s.get(HOST + '/web/image/website/1/favicon', timeout=30)
head = r.content[:8]
print('HTTP %s, %d bytes, 头部: %s' % (r.status_code, len(r.content), head.hex()))
ok = r.status_code == 200 and head[:4] == bytes.fromhex('00000100') and len(r.content) == len(buf.getvalue())
print('favicon 校验:', '通过 ✓' if ok else '失败 ✗')
assert ok, 'favicon 未生效'

# 4. 登录页引用是否带新 unique 参数
r = s.get(HOST + '/web/login', timeout=30)
import re
m = re.search(r'/web/image/website/1/favicon\?unique=([0-9a-f]+)', r.text)
print('登录页 favicon URL:', m.group(0) if m else '未找到')
