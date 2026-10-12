#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""看 utils-lib.js 的 post 实现，确认 data 格式"""
import re

from bt_api import quick

api = quick()

p = '/www/server/panel/BTPanel/static/js/utils-lib.js'
res = api.read_file(p)
body = res.get('data', '')
print('大小:', len(body))

# 找 post 方法定义
for m in re.finditer(r'post\s*[:(=]', body):
    s = max(0, m.start() - 100)
    ctx = body[s:m.end() + 500]
    if 'function' in ctx or '=>' in ctx or 'async' in ctx:
        print('----- post 定义 -----')
        print(ctx[:600])
        print()
        break

# 找 request_token 相关
for m in re.finditer(r'request_token', body):
    s = max(0, m.start() - 200)
    print('----- token 上下文 -----')
    print(body[s:m.end() + 300])
    print()
    break
