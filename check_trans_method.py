#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查翻译加载方法签名 + 用 odoo shell 重载翻译"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -n '_load_translations\\|def button' /opt/odoo20/addons/base/models/ir_module.py | head; "
             "grep -rn 'def ' /opt/odoo20/addons/base/wizard/base_language_install.py | head",
             timeout=30, name='peek9')
print(out[:2500])
