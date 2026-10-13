#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全局找 header 电话模板"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -rn 'o_nav-link_secondary' /opt/odoo20/addons/website/views/*.xml | grep -i 'tel\\|phone' | head -5; echo =====; "
             "grep -rln 'tel:+1 555' /opt/odoo20/addons/website/views/ /opt/odoo20/addons/website/templates/ 2>/dev/null; echo =====; "
             "ls /opt/odoo20/addons/website/views/ | grep -i head",
             timeout=40, name='peek22')
print(out[:2000])
