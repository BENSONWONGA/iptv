#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝塔计划任务命令执行器
用法:
    python3 bt_cmd.py "任意shell命令"        # 执行并返回输出
"""
import json
import sys
import time

from bt_api import quick

TASK_NAME = 'deploy-pass'


class CmdRunner:

    def __init__(self):
        self.api = quick()
        self.crons = self._list()

    def _list(self):
        r = self.api.post('/crontab?action=GetCrontab', {})
        return r if isinstance(r, list) else []

    def find_task(self):
        for c in self.crons:
            if c.get('name') == TASK_NAME:
                return c
        return None

    def ensure_task(self, cmd):
        """创建或更新计划任务"""
        old = self.find_task()
        if old:
            # 删除旧任务
            self.api.post('/crontab?action=DelCrontab', {'id': old['id']})
            time.sleep(1)
        r = self.api.post('/crontab?action=AddCrontab', {
            'name': TASK_NAME,
            'type': 'minute-n', 'where1': '9999',
            'hour': '', 'minute': '', 'week': '', 'sType': 'toShell',
            'sbody': cmd, 'backupTo': 'localhost', 'save': '', 'urladdress': '',
        })
        return r

    def exec_and_read(self, cmd, wait=3, reads=6):
        r = self.ensure_task(cmd)
        if not (isinstance(r, dict) and (r.get('status') or r.get('id'))):
            return {'create_failed': r}
        time.sleep(1)
        self.crons = self._list()
        task = self.find_task()
        if not task:
            return {'task_not_found': r}
        echo, tid = task.get('echo'), task['id']
        # 立即执行
        er = self.api.post('/crontab?action=StartCrontab_api', {'id': tid, 'echo': echo})
        # 轮询读日志
        time.sleep(wait)
        for i in range(reads):
            logs = self.api.post('/crontab?action=GetLogsApi', {'id': tid, 'echo': echo})
            body = ''
            if isinstance(logs, dict):
                body = logs.get('msg', '') or logs.get('data', '') or logs.get('log', '')
                if not body and logs.get('status'):
                    body = json.dumps(logs, ensure_ascii=False)
            if body and ('CMD_DONE' in str(body)):
                return body
            time.sleep(2)
        return body or {'no_output': logs}

    def cleanup(self):
        task = self.find_task()
        if task:
            self.api.post('/crontab?action=DelCrontab', {'id': task['id']})


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'echo hello && echo CMD_DONE'
    runner = CmdRunner()
    out = runner.exec_and_read(cmd + '\necho "__CMD_DONE__"')
    print(out)
    runner.cleanup()
