#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""品牌收尾：用新 logo 生成方形 favicon 并写入 website.favicon"""
import base64
import io
import json

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
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
uid = r.json()['result']['uid']
print('RPC 登录 ✓ uid=%s' % uid)

# 1. 读取上传的原始 logo，裁边并放入方形画布
img = Image.open('/workspace/.uploads/31c555f2-339a-4f75-b82b-03028e55105b_奥登科logops.png').convert('RGBA')
print('原始尺寸:', img.size)
bbox = img.getbbox()
trimmed = img.crop(bbox) if bbox else img
w, h = trimmed.size
print('裁边后:', trimmed.size)

# 方形画布 256x256，logo 居中（宽则按宽缩放，上下留空）
canvas = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
scale = min(256 / w, 256 / h)
nw, nh = int(w * scale), int(h * scale)
resized = trimmed.resize((nw, nh), Image.LANCZOS)
canvas.paste(resized, ((256 - nw) // 2, (256 - nh) // 2), resized)
buf = io.BytesIO()
canvas.save(buf, format='PNG', optimize=True)
fav_b64 = base64.b64encode(buf.getvalue()).decode()
print('favicon 生成 ✓ %d bytes (base64 %d)' % (len(buf.getvalue()), len(fav_b64)))

# 2. 写入 website.favicon（Odoo 20 二进制字段 dict 格式）
rpc('website', 'write', [[1], {'favicon': {'filename': 'favicon.png', 'content': fav_b64}}])
print('website.favicon 已更新 ✓')

# 3. 回读确认
w1 = rpc('website', 'search_read', [[['id', '=', 1]], ['name', 'favicon']]) [0]
fc = w1['favicon']
content = fc.get('content', '') if isinstance(fc, dict) else (fc or '')
print('回读 favicon 前 40 字符:', content[:40], '长度:', len(content))
assert content.startswith('iVBORw0KGgo'), 'favicon 不是 PNG!'
print('全部完成 ✓')
