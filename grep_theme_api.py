#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 Odoo 20 源码中找主题应用机制"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run(
    'grep -rn "def.*theme" /opt/odoo20/addons/website/models/website.py 2>/dev/null | head -10; echo ---; '
    'grep -rn "theme" /opt/odoo20/addons/website/models/ir_ui_view.py 2>/dev/null | grep -iE "def|apply|switch" | head -5; echo ---; '
    'grep -rln "switch_theme\\|_apply_theme\\|apply_theme" /opt/odoo20/addons/website/ /opt/odoo20/addons/web/ 2>/dev/null | head -8; echo ---; '
    'grep -rn "def.*theme" /opt/odoo20/addons/website/models/website_theme.py 2>/dev/null | head; ls /opt/odoo20/addons/website/models/ | grep -i theme',
    timeout=60, name='src-grep')
print(out)
