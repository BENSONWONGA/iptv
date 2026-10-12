#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通过 /crontab/StartTask 执行计划任务 + 读日志"""
import json
import time

from bt_api import quick

api = quick()

crons = api.post('/crontab?action=GetCrontab', {})
task = next((c for c in crons if c.get('name') == 'deploy-pass'), None)
if not task:
    print('任务不存在!')
    raise SystemExit(1)
print('任务 id=%s echo=%s' % (task['id'], task['echo']))

# 新版 RESTful 格式执行
er = api.post('/crontab/StartTask', {'id': task['id'], 'echo': task['echo']})
print('exec:', json.dumps(er, ensure_ascii=False)[:300])

time.sleep(4)
lr = api.post('/crontab/GetLogs', {'id': task['id'], 'echo': task['echo']})
print('日志:', json.dumps(lr, ensure_ascii=False)[:500])
