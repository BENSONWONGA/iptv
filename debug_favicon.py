#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试 favicon 写入：获取完整 traceback"""
import json
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()

r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
print('uid =', r.json()['result']['uid'])

# 1x1 PNG（用 PIL 生成，避免手写 hex 出错）
import base64
import io
from PIL import Image

buf = io.BytesIO()
Image.new('RGBA', (16, 16), (230, 126, 34, 255)).save(buf, format='PNG')
png = base64.b64encode(buf.getvalue()).decode()

for fmt_name, val in [
    ('str', png),
    ('dict', {'filename': 'favicon.png', 'content': png}),
]:
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': 'website', 'method': 'write', 'args': [[1], {'favicon': val}], 'kwargs': {}}}, timeout=60)
    d = r.json()
    if 'error' in d:
        dbg = d['error'].get('data', {}).get('debug', '')
        print('=== %s 失败 ===' % fmt_name)
        print(dbg[-1800:])
    else:
        print('=== %s 成功! ===' % fmt_name)
        break
