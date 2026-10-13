#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查登录页布局模板与资源"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -rn 'oe_website_login_container\\|login_layout' /opt/odoo20/addons/web/views/weblogin_templates.xml 2>/dev/null | head -10; echo =====; "
             "ls /opt/odoo20/addons/web/views/ | grep -i login; echo =====; "
             "grep -n 'template id' /opt/odoo20/addons/web/views/weblogin_templates.xml | head -10; echo =====; "
             "grep -rn 'oe_website_login_container' /opt/odoo20/addons/website/ 2>/dev/null | head -5",
             timeout=40, name='peek-login1')
print(out[:3500])
