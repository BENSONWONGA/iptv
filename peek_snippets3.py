#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 Odoo 20 snippet 模板源码"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("ls /opt/odoo20/addons/website/views/ | head -30; echo ---; "
             "grep -rln 's_banner' /opt/odoo20/addons/website/views/*.xml | head -5; echo ---; "
             "find /opt/odoo20/addons/website -name '*.xml' -path '*snippets*' | head",
             timeout=40, name='peek6')
print(out[:3000])
