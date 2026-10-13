#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查 title 生成机制"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -n 'title' /opt/odoo20/addons/website/views/website_templates.xml | grep -iE 't-set|t-esc|t-out|<title' | head -8; echo =====; "
             "sed -n '117,130p' /opt/odoo20/addons/website_sale/templates/shop_page_templates.xml",
             timeout=40, name='peek18')
print(out[:2200])
