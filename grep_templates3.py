#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确定相关模板 key"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -n '<template' /opt/odoo20/addons/website_sale/templates/product_tile_templates.xml | head -10; echo ---; "
             "sed -n '3205,3228p' /opt/odoo20/addons/website/views/website_templates.xml; echo ---; "
             "grep -rn 'All products\\|Specifications' /opt/odoo20/addons/website_sale/templates/product_templates.xml /opt/odoo20/addons/website_sale/views/templates.xml 2>/dev/null | head -6",
             timeout=40, name='peek14')
print(out[:3500])
