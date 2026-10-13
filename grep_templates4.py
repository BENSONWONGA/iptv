#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找 searchbox 调用点与 All products/Specifications 模板"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -rn 'website_search_box' /opt/odoo20/addons/website_sale/templates/ /opt/odoo20/addons/website/templates/ /opt/odoo20/addons/website/views/ 2>/dev/null | grep -v 'template id' | head -6; echo ---; "
             "grep -rn 'All products' /opt/odoo20/addons/website_sale/ --include='*.xml' 2>/dev/null | head -4; echo ---; "
             "grep -rn 'Specifications' /opt/odoo20/addons/website_sale/ --include='*.xml' 2>/dev/null | head -4",
             timeout=40, name='peek15')
print(out[:3000])
