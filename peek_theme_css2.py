#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读主题变量与核心配色"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("cat /opt/odoo20/addons/theme_liquid_glass/static/src/scss/variables.scss; echo =====HEAD40; "
             "head -120 /opt/odoo20/addons/theme_liquid_glass/static/src/scss/glass_theme.scss",
             timeout=40, name='peek-theme2')
print(out[:7000])
