#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找 base 模块路径和翻译方法"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("find /opt/odoo20 -name 'base_language_install.py' 2>/dev/null | head -3; "
             "find /opt/odoo20 -name 'ir_module.py' 2>/dev/null | head -3; "
             "ls /opt/odoo20/odoo/addons 2>/dev/null | head -5",
             timeout=40, name='peek10')
print(out[:1500])
