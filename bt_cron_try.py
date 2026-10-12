#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AddCrontab 参数组合测试"""
import json
import time

from bt_api import quick

api = quick()

def ls_crons():
    r = api.post('/crontab?action=GetCrontab', {})
    return r if isinstance(r, list) else []

# 先删旧任务
for c in ls_crons():
    if c.get('name') == 'deploy-pass':
        api.post('/crontab?action=DelCrontab', {'id': c['id']})
        print('已删旧任务', c['id'])

variants = [
    {  # v1: 补全所有时间字段为空字符串
        'name': 'deploy-pass', 'type': 'minute-n', 'where1': '9999',
        'where_hour': '', 'where_minute': '',
        'hour': '00', 'minute': '00', 'week': '1',
        'sType': 'toShell', 'sbody': 'echo TEST_V1; echo __CMD_DONE__',
        'backupTo': 'localhost', 'save': '', 'urladdress': '', 'sName': '',
    },
    {  # v2: type=day 完整参数
        'name': 'deploy-pass', 'type': 'day', 'where1': '',
        'where_hour': '3', 'where_minute': '30',
        'hour': '3', 'minute': '30', 'week': '',
        'sType': 'toShell', 'sbody': 'echo TEST_V2; echo __CMD_DONE__',
        'backupTo': 'localhost', 'save': 'bash', 'urladdress': '',
    },
]
for i, v in enumerate(variants, 1):
    r = api.post('/crontab?action=AddCrontab', v)
    print('v%d => %s' % (i, json.dumps(r, ensure_ascii=False)[:200]))
    if isinstance(r, dict) and r.get('status'):
        break
    # 清理可能创建一半的
    for c in ls_crons():
        if c.get('name') == 'deploy-pass':
            api.post('/crontab?action=DelCrontab', {'id': c['id']})

print('当前任务列表:', [c.get('name') for c in ls_crons()])
