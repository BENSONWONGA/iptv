#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 theme_models.py 与预览 URL 逻辑"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run(
    'sed -n "1,120p" /opt/odoo20/addons/website/models/theme_models.py; echo ===780-830===; '
    'sed -n "780,830p" /opt/odoo20/addons/website/models/website.py',
    timeout=60, name='src-read')
print(out)
