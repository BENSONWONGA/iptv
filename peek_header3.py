#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确认 3541 行所在模板"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("awk 'NR<=3541 && /<template/ {print NR\": \"$0}' /opt/odoo20/addons/website/views/website_templates.xml | tail -2; echo =====; "
             "sed -n '3535,3548p' /opt/odoo20/addons/website/views/website_templates.xml",
             timeout=40, name='peek23')
print(out[:2000])
