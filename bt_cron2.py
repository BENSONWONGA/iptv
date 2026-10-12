#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AddCrontab 正确字段名(sBody) + 执行 + 日志接口测试"""
import json
import time

from bt_api import quick

api = quick()

def crons():
    r = api.post('/crontab?action=GetCrontab', {})
    return r if isinstance(r, list) else []

# 清理旧 deploy-pass
for c in crons():
    if c.get('name') == 'deploy-pass':
        api.post('/crontab?action=DelCrontab', {'id': c['id']})
        print('删旧任务', c['id'])

# 用正确字段名创建
r = api.post('/crontab?action=AddCrontab', {
    'name': 'deploy-pass', 'type': 'day', 'where1': '3',
    'where_hour': 3, 'where_minute': 30,
    'hour': '3', 'minute': '30', 'week': '',
    'sType': 'toShell', 'sBody': 'echo TEST_EXEC_OK; id; echo __CMD_DONE__',
    'backupTo': 'localhost', 'save': '保存计划任务',
    'sName': '', 'urladdress': '',
})
print('创建:', json.dumps(r, ensure_ascii=False)[:200])

time.sleep(1.5)
task = next((c for c in crons() if c.get('name') == 'deploy-pass'), None)
if not task:
    print('任务未创建!')
    raise SystemExit(1)
print('任务 id=%s echo=%s' % (task['id'], task['echo']))

# 执行接口变体
for act in ['StartCrontab_api', 'start_task', 'ExecCrontab', 'exec_cron']:
    er = api.post('/crontab?action=%s' % act, {'id': task['id'], 'echo': task['echo']})
    s = json.dumps(er, ensure_ascii=False)[:150]
    print('exec[%s] => %s' % (act, s))
    if isinstance(er, dict) and er.get('status'):
        break

time.sleep(3)
# 日志接口变体
for act in ['GetLogsApi', 'get_logs', 'GetLogs', 'get_log']:
    lr = api.post('/crontab?action=%s' % act, {'id': task['id'], 'echo': task['echo']})
    s = json.dumps(lr, ensure_ascii=False)[:250]
    print('logs[%s] => %s' % (act, s))
    if isinstance(lr, dict) and lr.get('status'):
        break
