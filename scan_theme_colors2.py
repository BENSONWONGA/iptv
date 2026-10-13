#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精确扫描：白色文字/边框、深色背景、滚动条"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("cd /opt/odoo20/addons/theme_liquid_glass/static/src/scss && "
             "echo '=== A. 白色文字 color ==='; grep -n 'color: *#fff\\|color: *white\\|color: *rgba(255' *.scss; "
             "echo '=== B. 深色背景 ==='; grep -n 'background[^:]*: *rgba(1[0-9],\\|background[^:]*: *rgba(2[0-9],\\|background[^:]*: *rgba(7[0-9],\\|background[^:]*: *#0\\|background[^:]*: *#1\\|background[^:]*: *#2' *.scss; "
             "echo '=== C. 滚动条 ==='; grep -n 'scrollbar' *.scss; "
             "echo '=== D. rgba(255,255,255 全部行号 ==='; grep -n 'rgba(255, 255, 255' glass_theme.scss | head -50",
             timeout=40, name='peek-theme5')
print(out[:8000])
