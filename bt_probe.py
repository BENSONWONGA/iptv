#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝塔面板 API 探测"""
import json
import sys

from bt_login import BTClient

c = BTClient()
assert c.login(), '登录失败'

probes = [
    ('POST', '/ajax?action=GetPanelVersion', {}),
    ('POST', '/system?action=GetSystemTotal', {}),
    ('POST', '/crontab/list', {'p': 1, 'limit': 5}),
    ('POST', '/plugin?action=get_plugin_list', {}),
    ('POST', '/config?action=get_config', {}),
]
for method, path, data in probes:
    try:
        r = c.post(path, data) if method == 'POST' else None
        out = json.dumps(r, ensure_ascii=False)
        print('[%s] %s => %s' % (method, path, out[:220]))
    except Exception as e:
        print('[%s] %s => ERR %s' % (method, path, e))
    print('-' * 60)
