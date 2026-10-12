#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝塔 API 完整客户端：登录 + x-http-token + 常用操作"""
import json
import re

from bt_login import BTClient


class BTAPI(BTClient):

    def init_token(self):
        r = self.s.get('http://220.162.99.166:8900/', timeout=15)
        m = re.search(r"vite_public_request_token\s*=\s*'([^']+)'", r.text)
        if not m:
            raise RuntimeError('未取到 request_token')
        self.s.headers['x-http-token'] = m.group(1)

    def get(self, path, params=None):
        r = self.s.get('http://220.162.99.166:8900' + path, params=params, timeout=60)
        try:
            return r.json()
        except Exception:
            return {'_raw': r.text[:800], '_code': r.status_code}

    def post(self, path, data=None):
        r = self.s.post('http://220.162.99.166:8900' + path, data=data or {}, timeout=60)
        try:
            return r.json()
        except Exception:
            return {'_raw': r.text[:800], '_code': r.status_code}

    def read_file(self, path):
        return self.post('/files?action=GetFileBody', {'path': path})

    def exec_cmd(self, cmd):
        """通过计划任务执行命令（先创建再立即执行再读日志）"""
        # 1. 创建
        res = self.post('/crontab?action=AddCrontab', {
            'name': 'deploypass', 'type': 'minute-n', 'where1': '100',
            'hour': '', 'minute': '', 'week': '', 'sType': 'toShell',
            'sbody': cmd, 'backupTo': 'localhost', 'save': '', 'urladdress': '',
        })
        return res


def quick():
    api = BTAPI()
    assert api.login()
    api.init_token()
    return api


if __name__ == '__main__':
    api = quick()
    # 探测 Odoo 配置文件位置
    for p in ['/etc/odoo.conf', '/etc/odoo/odoo.conf', '/www/server/odoo/conf/odoo.conf',
              '/etc/odoo-server.conf', '/opt/odoo/conf/odoo.conf']:
        res = api.read_file(p)
        s = json.dumps(res, ensure_ascii=False)
        print(p, '=>', s[:180])
    # 目录探测
    for p in ['/www/server', '/www/wwwroot', '/opt']:
        res = api.post('/files?action=GetDirList', {'path': p, 'p': 1, 'showRow': 30})
        if isinstance(res, dict) and res.get('status'):
            names = [f['filename'] for f in res.get('files', [])][:25]
            print(p, '目录:', names)
        else:
            print(p, '=>', json.dumps(res, ensure_ascii=False)[:100])
