#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 odoo20.conf 关键配置"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run('grep -vE "^(#|$)" /etc/odoo20.conf', timeout=30, name='conf-read')
print(out)
