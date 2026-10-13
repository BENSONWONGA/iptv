#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取翻译相关方法定义"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -n 'def ' /opt/odoo20/odoo/addons/base/wizard/base_language_install.py; echo ---; "
             "grep -n '_load_translations' /opt/odoo20/odoo/addons/base/models/ir_module.py | head -5",
             timeout=30, name='peek11')
print(out[:2000])
