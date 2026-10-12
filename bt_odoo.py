#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宝塔：读取 Odoo20 配置"""
import json

from bt_api import quick

api = quick()

def ls(path):
    r = api.post('/files?action=GetDir&path=%s' % path, {})
    if isinstance(r, dict) and 'DIR' in r:
        return [d.split(';')[0] for d in r['DIR']]
    return None

for p in ['/opt/odoo20', '/home/odoo20', '/etc']:
    names = ls(p)
    if names:
        rel = [n for n in names if 'odoo' in n.lower() or n.endswith('.conf') or n == 'systemd']
        print(p, '=>', rel[:15] if rel else names[:12])

# 直接尝试读配置
for f in ['/opt/odoo20/odoo.conf', '/opt/odoo20/conf/odoo.conf', '/etc/odoo20.conf',
          '/etc/odoo20/odoo.conf', '/home/odoo20/odoo.conf', '/opt/odoo20/odoo20.conf',
          '/etc/systemd/system/odoo20.service', '/etc/systemd/system/odoo.service']:
    r = api.read_file(f)
    if isinstance(r, dict) and r.get('status'):
        print('===== %s =====' % f)
        print(r.get('data', r.get('DATA', ''))[:700] if isinstance(r.get('data', r.get('DATA')), str) else json.dumps(r, ensure_ascii=False)[:500])
        break
    else:
        msg = r.get('msg', '') if isinstance(r, dict) else ''
        print(f, '=>', msg[:50])
