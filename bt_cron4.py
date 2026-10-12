#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""动态 token（proxy_key为空）调 StartTask"""
import hashlib
import json
import time

from bt_login import BTClient

MD5_EMPTY = hashlib.md5(b'').hexdigest()


class BT2(BTClient):
    def init_token(self):
        import re
        r = self.s.get('http://220.162.99.166:8900/', timeout=15)
        m = re.search(r"vite_public_request_token\s*=\s*'([^']+)'", r.text)
        self.s.headers['x-http-token'] = m.group(1)

    def dyn(self):
        ts = int(time.time() * 1000)
        tok = hashlib.md5(('%d%s' % (ts, MD5_EMPTY)).encode()).hexdigest()
        return ts, tok

    def post_v2(self, path, data, wrap_json=False):
        ts, tok = self.dyn()
        d = dict(data)
        d['request_time'] = ts
        d['request_token'] = tok
        url = 'http://220.162.99.166:8900' + path
        if wrap_json:
            r = self.s.post(url, json=d, timeout=60)
        else:
            r = self.s.post(url, data=d, timeout=60)
        try:
            return r.json()
        except Exception:
            return {'_raw': r.text[:300], '_code': r.status_code}


bt = BT2()
assert bt.login()
bt.init_token()

# GetCrontab（旧格式可用）
crons = bt.post('/crontab?action=GetCrontab', {}) if hasattr(bt, 'post') else None
if crons is None:
    crons = bt.post_v2('/crontab/GetCrontab', {})
task = next((c for c in crons if c.get('name') == 'deploy-pass'), None)
print('任务:', task['id'], task['echo'] if task else '无')

params = {'id': task['id'], 'echo': task['echo']}

# 变体测试
r1 = bt.post_v2('/crontab/StartTask', params, wrap_json=False)
print('form:', json.dumps(r1, ensure_ascii=False)[:200])

r2 = bt.post_v2('/crontab/StartTask', params, wrap_json=True)
print('json:', json.dumps(r2, ensure_ascii=False)[:200])

time.sleep(4)
lr = bt.post('/crontab?action=GetLogs', {'id': task['id'], 'echo': task['echo']}) if hasattr(bt, 'post') else bt.post_v2('/crontab/GetLogs', params)
print('日志:', json.dumps(lr, ensure_ascii=False)[:600])
