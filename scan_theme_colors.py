#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描主题所有颜色定义位置"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("cd /opt/odoo20/addons/theme_liquid_glass/static/src/scss && "
             "echo '--- bg-img 引用 ---'; grep -n 'bg-img' *.scss; "
             "echo '--- 深色背景 (dark/navy/black背景) ---'; grep -n 'background[^;]*#\\|background[^;]*rgba([0-9]\\+, [0-9]\\+, [0-9]\\+' glass_theme.scss navbar.scss | head -30; "
             "echo '--- 硬编码白色文字 ---'; grep -cn 'rgba(255, 255, 255' glass_theme.scss; grep -c '#fff\\|white' glass_theme.scss 2>/dev/null; "
             "echo '--- navbar.scss 全文 ---'; cat navbar.scss | head -100",
             timeout=40, name='peek-theme4')
print(out[:6000])
