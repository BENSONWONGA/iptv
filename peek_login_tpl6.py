#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读 web.login_layout (107行起) 与 web.login (161行附近)"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("sed -n '105,175p' /opt/odoo20/addons/web/views/webclient_templates.xml",
             timeout=40, name='peek-login6')
print(out[:5000])
