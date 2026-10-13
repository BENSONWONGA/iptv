#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找 header 电话模板 + 菜单翻译验证"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("awk 'NR<=1812 && /<template/ {print NR\": \"$0}' /opt/odoo20/addons/website/views/website_templates.xml | tail -2; echo =====; "
             "sed -n '1800,1816p' /opt/odoo20/addons/website/views/website_templates.xml",
             timeout=40, name='peek21')
print(out[:2200])
