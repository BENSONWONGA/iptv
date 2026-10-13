#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取模板id与搜索框源码位置"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("sed -n '235,255p' /opt/odoo20/addons/website_sale/templates/product_tile_templates.xml; echo ---; "
             "grep -rn 'oe_search_box' /opt/odoo20/addons/website/templates/ /opt/odoo20/addons/website/views/ /opt/odoo20/addons/website/static/src/snippets/s_searchbar/ 2>/dev/null | head -4; echo ---; "
             "grep -rn 'placeholder' /opt/odoo20/addons/website/static/src/snippets/s_searchbar/000.xml 2>/dev/null",
             timeout=40, name='peek13')
print(out[:3000])
