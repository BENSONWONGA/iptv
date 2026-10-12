#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 16689 端口（用户浏览器实际登录的端口）的 API"""
import json
import re

import requests


BASE2 = 'http://220.162.99.166:16689'

s = requests.Session()
s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# 1. 看主页是否能访问
try:
    r = s.get(BASE2 + '/', timeout=10)
    print('主页状态:', r.status_code, '长度:', len(r.text))
    m = re.search(r"vite_public_request_token\s*=\s*'([^']+)'", r.text)
    if m:
        s.headers['x-http-token'] = m.group(1)
        print('request_token:', m.group(1)[:20] + '...')
    m2 = re.search(r"login_token\s*[:=]\s*['\"]([^'\"]+)['\"]", r.text)
    print('login_token:', m2.group(1) if m2 else '未找到')
except Exception as e:
    print('16689 主页访问失败:', e)
    raise SystemExit(1)
