#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""定位 Add to Cart / Search 模板"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -rn 'Add to Cart' /opt/odoo20/addons/website_sale/templates/ /opt/odoo20/addons/website_sale/views/ 2>/dev/null | head -5; echo ---; "
             "grep -rn 'placeholder=\"Search' /opt/odoo20/addons/website/ 2>/dev/null | grep -v '.js:' | head -5",
             timeout=40, name='peek12')
print(out[:2500])
