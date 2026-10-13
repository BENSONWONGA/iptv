#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拿 Specifications Accordion 模板id + search_box_input 定义"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("sed -n '1465,1472p' /opt/odoo20/addons/website_sale/templates/product_page_templates.xml; echo =====; "
             "grep -n 'website_search_box_input' /opt/odoo20/addons/website/views/website_templates.xml | head -3; echo =====; "
             "grep -rn 'placeholder=\"Search\\.\\.\\.\"' /opt/odoo20/addons/website/views/website_templates.xml /opt/odoo20/addons/website/templates/ 2>/dev/null | head -4",
             timeout=40, name='peek17')
print(out[:2500])
