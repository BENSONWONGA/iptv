#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝塔 API 认证头测试"""
import json

from bt_login import BTClient

c = BTClient()
assert c.login(), '登录失败'

print('cookies:', c.s.cookies.get_dict())

# 尝试多种认证头
cookie_val = None
for name, val in c.s.cookies.get_dict().items():
    if name.lower() in ('request_token', 'x-http-token') or len(name) == 32:
        cookie_val = val
        break
print('token 候选:', cookie_val[:20] if cookie_val else None, '...')

for header_name in ['x-http-token', 'X-HTTP-TOKEN', 'http_token']:
    c.s.headers[header_name] = cookie_val
    r = c.post('/ajax?action=GetPanelVersion', {})
    print('[%s] => %s' % (header_name, json.dumps(r, ensure_ascii=False)[:150]))
    del c.s.headers[header_name]
