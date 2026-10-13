#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看 liquid_glass 主题 CSS 结构"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("ls -la /opt/odoo20/addons/theme_liquid_glass/static/src/scss/ /opt/odoo20/addons/theme_liquid_glass/static/src/css/ 2>/dev/null; echo =====; "
             "wc -l /opt/odoo20/addons/theme_liquid_glass/static/src/scss/*.scss 2>/dev/null; "
             "wc -l /opt/odoo20/addons/theme_liquid_glass/static/src/css/*.css 2>/dev/null",
             timeout=40, name='peek-theme1')
print(out[:3000])
