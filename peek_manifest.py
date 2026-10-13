#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读主题 manifest 资产注册 + bg-img 背景图"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("cat /opt/odoo20/addons/theme_liquid_glass/__manifest__.py; echo =====; "
             "ls /opt/odoo20/addons/theme_liquid_glass/static/src/img/",
             timeout=40, name='peek-theme3')
print(out[:4000])
