#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""排查：dt 目录状态 + 数据库创建表单参数"""
import re

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
ex = BTExec()

out = ex.run('ls -d /tmp/dt/theme_*/ 2>/dev/null; echo ---; cd /tmp/dt 2>/dev/null && git sparse-checkout list 2>/dev/null; echo ---STATUS---; cd /tmp/dt 2>/dev/null && git status --short 2>&1 | head -3',
             timeout=60, name='dt-check')
print(out)
print('=' * 50)

# 看数据库管理器表单的字段名
r = requests.get(HOST + '/web/database/manager', timeout=60)
html = r.text
print('manager 页 HTTP', r.status_code, '长度', len(html))
# 提取 create 表单的 input/select 字段
names = re.findall(r'<(?:input|select|button)[^>]*name="([^"]+)"', html)
print('表单字段:', sorted(set(names)))
# 找 create 相关的 action
acts = re.findall(r'(?:action|data-action)="([^"]*create[^"]*)"', html)
print('create 动作:', sorted(set(acts)))
# 找模板下拉（Odoo 20 建库带模板选择）
tpls = re.findall(r'value="([^"]*)"[^>]*>[^<]*(?:template|Template)', html)
print('模板选项样例:', tpls[:10])
