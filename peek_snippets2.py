#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找 website snippet 模板"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("ls /opt/odoo20/odoo/addons/ | grep -i website; echo ---; "
             "ls /opt/odoo20/odoo/addons/website/ 2>/dev/null; echo ---; "
             "find /opt/odoo20/odoo/addons/website -maxdepth 3 -name '*.xml' | head -30",
             timeout=40, name='peek4')
print(out)
