#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝塔命令执行通道：创建任务 → 执行 → 读日志 → 清理"""
import json
import time
import uuid

from bt_api import quick


class BTExec:
    def __init__(self):
        self.api = quick()

    def _crons(self):
        r = self.api.post('/crontab?action=GetCrontab', {})
        return r if isinstance(r, list) else []

    def _find(self, name):
        return next((c for c in self._crons() if c.get('name') == name), None)

    def run(self, cmd, timeout=20, name=None):
        """执行 shell 命令并返回日志输出"""
        name = name or ('x-' + uuid.uuid4().hex[:10])
        # 清理同名旧任务
        old = self._find(name)
        if old:
            self.api.post('/crontab?action=DelCrontab', {'id': old['id']})
        # 创建
        r = self.api.post('/crontab?action=AddCrontab', {
            'name': name, 'type': 'day', 'where1': '3',
            'where_hour': 3, 'where_minute': 30,
            'hour': '3', 'minute': '30', 'week': '',
            'sType': 'toShell', 'sBody': cmd,
            'backupTo': 'localhost', 'save': '保存计划任务',
            'sName': '', 'urladdress': '',
        })
        if not (isinstance(r, dict) and r.get('status')):
            return '创建失败: %s' % json.dumps(r, ensure_ascii=False)[:200]
        task = self._find(name)
        if not task:
            return '任务未找到'
        # 执行（只传 id！）
        er = self.api.post('/crontab?action=StartTask', {'id': task['id']})
        if not (isinstance(er, dict) and er.get('status')):
            return '执行失败: %s' % json.dumps(er, ensure_ascii=False)[:200]
        # 轮询日志
        deadline = time.time() + timeout
        log = ''
        while time.time() < deadline:
            time.sleep(3)
            lr = self.api.post('/crontab?action=GetLogs', {'id': task['id'], 'echo': task['echo']})
            if isinstance(lr, dict) and lr.get('status'):
                log = lr.get('msg', '')
                break
        # 清理
        self.api.post('/crontab?action=DelCrontab', {'id': task['id']})
        return log


if __name__ == '__main__':
    import sys
    ex = BTExec()
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'echo HELLO; hostname'
    out = ex.run(cmd)
    print(out)
