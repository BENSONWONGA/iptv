#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确认青绿按钮白字上下文（需保留白色的位置）"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("cd /opt/odoo20/addons/theme_liquid_glass/static/src/scss && "
             "echo '=== modals 450-475 ==='; sed -n '450,475p' modals.scss; "
             "echo '=== modals 545-575 ==='; sed -n '545,575p' modals.scss; "
             "echo '=== glass 1505-1534 ==='; sed -n '1505,1534p' glass_theme.scss; "
             "echo '=== glass 1455-1495 ==='; sed -n '1455,1495p' glass_theme.scss; "
             "echo '=== lists 35-52 ==='; sed -n '35,52p' lists.scss; "
             "echo '=== navbar 125-150 ==='; sed -n '125,150p' navbar.scss",
             timeout=40, name='peek-theme7')
print(out[:8000])
