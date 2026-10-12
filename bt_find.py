#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝塔：浏览目录找 Odoo + 探测计划任务接口"""
import json

from bt_api import quick

api = quick()

def ls(path):
    r = api.post('/files?action=GetDir&path=%s' % path, {})
    if isinstance(r, dict) and 'DIR' in r:
        dirs = r['DIR']
        files = [f.get('filename', f.get('name')) for f in r.get('FILE', [])] if isinstance(r.get('FILE'), list) else []
        return [d if isinstance(d, str) else d.get('filename') for d in dirs], files, r
    return None, None, r

for p in ['/', '/www/server', '/opt', '/srv', '/home', '/root']:
    d, f, raw = ls(p)
    if d is not None:
        print('%s => %s' % (p, d[:30]))
    else:
        print('%s => FAIL %s' % (p, json.dumps(raw, ensure_ascii=False)[:80]))

# 根目录找 odoo 相关 systemd 服务
print('===== systemd 服务 =====')
r = api.read_file('/etc/systemd/system')
print('read /etc/systemd/system:', json.dumps(r, ensure_ascii=False)[:120])
