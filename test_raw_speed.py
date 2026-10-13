#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试服务器从 raw.githubusercontent 实际下载速度"""
import time

from bt_exec import BTExec

ex = BTExec()
# theme_kea 里的一张大图 + 一个文本文件
out = ex.run(
    'cd /tmp && rm -f spd.bin spd.py && '
    'time (curl -sS -m 60 -o spd.py https://raw.githubusercontent.com/odoo/design-themes/20.0/theme_kea/__manifest__.py) && '
    'IMG=$(curl -sS -m 30 "https://api.github.com/repos/odoo/design-themes/contents/theme_kea/static/src/img?ref=20.0" 2>/dev/null | head -5); echo "api: ${IMG:0:80}"; '
    'curl -sS -m 120 -o spd.bin "https://raw.githubusercontent.com/odoo/design-themes/20.0/theme_kea/static/src/img/content/image_01.svg" 2>&1; '
    'ls -la spd.py spd.bin 2>/dev/null; head -c 200 spd.py',
    timeout=180, name='spd-test')
print(out)
