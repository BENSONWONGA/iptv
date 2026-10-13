#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取产品相关 snippet 与 text_image/numbers"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("cat /opt/odoo20/addons/website/views/snippets/s_product_catalog.xml | head -60; echo ===SPLIT===; "
             "cat /opt/odoo20/addons/website/views/snippets/s_text_image.xml | head -40; echo ===SPLIT===; "
             "cat /opt/odoo20/addons/website/views/snippets/s_numbers.xml | head -40; echo ===SPLIT===; "
             "cat /opt/odoo20/addons/website_sale/templates/snippets/s_dynamic_snippet_products.xml | head -30",
             timeout=40, name='peek8')
print(out[:8000])
