#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""探测 Odoo 目录结构"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("ls /opt/odoo20/ 2>/dev/null; echo ---; "
             "ls /opt/odoo20/addons/ 2>/dev/null | head -30; echo ---; "
             "cat /etc/systemd/system/odoo20.service 2>/dev/null | grep -E 'ExecStart|WorkingDirectory'",
             timeout=30, name='peek3')
print(out)
