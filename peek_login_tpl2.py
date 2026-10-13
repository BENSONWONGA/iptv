#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""找 web 模块登录模板文件"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -rln 'oe_login_form' /opt/odoo20/odoo/addons/web/ /opt/odoo20/addons/web/ 2>/dev/null | grep -v '.py' | head -8; echo =====; "
             "grep -rn 'oe_website_login_container' /opt/odoo20/odoo/addons/web/ 2>/dev/null | grep xml | head -5; echo =====; "
             "sed -n '1760,1790p' /opt/odoo20/addons/website/views/website_templates.xml",
             timeout=40, name='peek-login2')
print(out[:3500])
