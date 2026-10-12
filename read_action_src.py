#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读服务器 http.py 的 call_kw/split_context"""
import re

from bt_api import quick

api = quick()

res = api.read_file('/opt/odoo20/odoo/http.py')
body = res.get('data', '')
print('文件大小:', len(body))

for pat in [r'def split_context\(.*?(?=\ndef |\nclass )', r'def call_kw\(.*?(?=\ndef |\nclass )',
            r'def call_kw_args\(.*?(?=\ndef |\nclass )']:
    m = re.search(pat, body, re.S)
    if m:
        print('--- %s ---' % pat[:20])
        print(m.group(0)[:1800])
        print()
