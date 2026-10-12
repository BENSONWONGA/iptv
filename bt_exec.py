#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝塔命令执行通道探测"""
import json

from bt_api import quick

api = quick()

print('===== 1. crontab 接口探测 =====')
tests = [
    ('/crontab?action=GetCrontab', {}),
    ('/crontab?action=get_crontab', {}),
    ('/crontab/list', {'p': 1, 'limit': 10, 'search': ''}),
    ('/crontab/GetCrontab', {}),
]
for path, data in tests:
    r = api.post(path, data)
    print('%s => %s' % (path, json.dumps(r, ensure_ascii=False)[:150]))

print('===== 2. 终端接口探测 =====')
tests = [
    ('/term?action=get_ssh_info', {}),
    ('/webssh?action=GetSshInfo', {}),
    ('/xterm/host_list', {}),
    ('/term/host_list', {}),
]
for path, data in tests:
    r = api.post(path, data)
    print('%s => %s' % (path, json.dumps(r, ensure_ascii=False)[:150]))

print('===== 3. 目录接口探测 =====')
tests = [
    ('/files?action=GetDirList', {'path': '/www/server', 'p': 1, 'showRow': 30, 'isDir': True}),
    ('/files?action=get_dir_list', {'path': '/www/server', 'p': 1, 'showRow': 30}),
    ('/files?action=GetDir&path=/www/server', {}),
]
for path, data in tests:
    r = api.post(path, data)
    print('%s => %s' % (path, json.dumps(r, ensure_ascii=False)[:200]))
