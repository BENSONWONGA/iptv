#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看已有计划任务详情 + 日志（找 reset_crm_pwd 的命令格式）"""
import json

from bt_api import quick

api = quick()

crons = api.post('/crontab?action=GetCrontab', {})
print('任务数:', len(crons))
for c in crons:
    if c.get('name') in ('reset_crm_pwd', 'show_crm_db_config', 'migrate_status_benson_crm'):
        print('===== %s (id=%s) =====' % (c['name'], c['id']))
        print(json.dumps(c, ensure_ascii=False)[:600])
        # 读日志
        logs = api.post('/crontab?action=GetLogsApi', {'id': c['id'], 'echo': c.get('echo')})
        body = logs.get('msg', '') if isinstance(logs, dict) else str(logs)
        print('--- 日志 ---')
        print(body[:800])
        print()

# 顺便看普通任务完整字段（了解结构）
print('===== 样例任务字段 =====')
print(json.dumps(crons[0], ensure_ascii=False)[:500])
