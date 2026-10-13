#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找 odoo.conf 的 addons_path"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("cat /etc/odoo20.conf | grep -v -E 'db_password|admin_passwd'; echo ---; "
             "ls /opt/odoo20/odoo/ | head; echo ---; "
             "find / -maxdepth 4 -type d -name 'website_sale' 2>/dev/null | head -5",
             timeout=60, name='peek5')
print(out)
