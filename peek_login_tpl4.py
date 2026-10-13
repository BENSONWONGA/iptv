#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全局找 web.login 模板定义"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -rln 'login_layout' /opt/odoo20/addons/web/views/ 2>/dev/null; echo =====; "
             "ls /opt/odoo20/addons/web/views/ | head -30",
             timeout=40, name='peek-login4')
print(out[:2000])
