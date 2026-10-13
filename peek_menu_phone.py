#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查 navbar 菜单渲染逻辑 + 电话模板"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("awk 'NR<=2035 && /<template/ {print NR\": \"$0}' /opt/odoo20/addons/website/views/website_templates.xml | tail -2; echo =====; "
             "grep -n 'menu_id\\|main_menu' /opt/odoo20/addons/website/views/website_templates.xml | head -8; echo =====; "
             "sed -n '2025,2040p' /opt/odoo20/addons/website/views/website_templates.xml",
             timeout=40, name='peek20')
print(out[:3000])
