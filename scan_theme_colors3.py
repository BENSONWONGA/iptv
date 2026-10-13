#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补充扫描：modals白色 + 1284上下文 + buttons/forms"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("cd /opt/odoo20/addons/theme_liquid_glass/static/src/scss && "
             "echo '=== modals.scss 白色rgba ==='; grep -n 'rgba(255, 255, 255\\|#fff\\|white' modals.scss | head -40; "
             "echo '=== glass 1280-1290 ==='; sed -n '1280,1290p' glass_theme.scss; "
             "echo '=== buttons.scss ==='; cat buttons.scss | head -76; "
             "echo '=== forms.scss 白色/深色 ==='; grep -n 'rgba(255\\|#fff\\|white\\|rgba(0,\\|rgba(1[0-9],\\|rgba(2[0-9],' forms.scss | head -20; "
             "echo '=== caret ==='; grep -rn 'caret-color' *.scss",
             timeout=40, name='peek-theme6')
print(out[:8000])
