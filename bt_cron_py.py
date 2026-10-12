#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""搜'指定参数无效'来源 + 测试 StartTask 只传 id"""
import json
import time

from bt_api import quick

api = quick()

# 1. 搜 crontab.py 中"指定参数无效"的位置
res = api.read_file('/www/server/panel/class/crontab.py')
body = res.get('data', '')
idx = body.find('指定参数无效')
if idx >= 0:
    print('--- crontab.py 中的上下文 ---')
    print(body[max(0, idx - 500):idx + 100])
else:
    print('crontab.py 中没有该错误消息，来自其他层')

# 2. 测试 StartTask 各变体
crons = api.post('/crontab?action=GetCrontab', {})
task = next((c for c in crons if c.get('name') == 'deploy-pass'), None)
print('任务 id:', task['id'], 'echo:', task['echo'])

variants = [
    ('action + 只传id', '/crontab?action=StartTask', {'id': task['id']}),
    ('action + id字符串', '/crontab?action=StartTask', {'id': str(task['id'])}),
    ('restful + 只传id', '/crontab/StartTask', {'id': task['id']}),
]
for name, path, data in variants:
    r = api.post(path, data)
    print('[%s] %s =>' % (name, path), json.dumps(r, ensure_ascii=False)[:150])

time.sleep(5)
lr = api.post('/crontab?action=GetLogs', {'id': task['id'], 'echo': task['echo']})
print('日志:', json.dumps(lr, ensure_ascii=False)[:600])
