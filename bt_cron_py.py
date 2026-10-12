#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找宝塔 crontab 控制器代码中的 StartTask"""
import re

from bt_api import quick

api = quick()

# 可能的路径
paths = [
    '/www/server/panel/class_v2/crontab.py',
    '/www/server/panel/class/crontab.py',
    '/www/server/panel/mod/project/crontab/crontab.py',
    '/www/server/panel/mod/crontab/crontab.py',
]

for p in paths:
    res = api.read_file(p)
    body = res.get('data', '') if isinstance(res, dict) else ''
    print('===== %s (%d 字节) status=%s =====' % (p, len(body), res.get('status') if isinstance(res, dict) else '?'))
    if body and len(body) > 100:
        # 找 StartTask 方法定义
        for m in re.finditer(r'def\s+(StartTask|start_task|StartCrontab)', body):
            s = max(0, m.start() - 50)
            print('--- %s ---' % m.group(1))
            print(body[s:m.end() + 800])
            print()
        # 找 "指定参数无效" 的来源
        for m in re.finditer(r'指定参数无效', body):
            s = max(0, m.start() - 300)
            print('--- 错误来源 ---')
            print(body[s:m.end() + 100])
            print()
            break
        break
