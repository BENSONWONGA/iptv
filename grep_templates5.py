#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收集模板上下文"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("sed -n '1,14p' /opt/odoo20/addons/website_sale/templates/shop_page_templates.xml; echo =====; "
             "sed -n '292,304p' /opt/odoo20/addons/website_sale/templates/shop_page_templates.xml; echo =====; "
             "awk 'NR<=300 && /<template/ {print NR\": \"$0}' /opt/odoo20/addons/website_sale/templates/shop_page_templates.xml | tail -3; echo =====; "
             "sed -n '750,772p' /opt/odoo20/addons/website_sale/templates/product_page_templates.xml; echo =====; "
             "awk 'NR<=1450 && /<template/ {print NR\": \"$0}' /opt/odoo20/addons/website_sale/templates/product_page_templates.xml | tail -2; echo =====; "
             "sed -n '1485,1495p' /opt/odoo20/addons/website_sale/templates/product_page_templates.xml",
             timeout=40, name='peek16')
print(out[:4500])
