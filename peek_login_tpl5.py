#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读 webclient_templates.xml 中 login_layout 完整定义"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -n 'login_layout\\|template id=\"login\"' /opt/odoo20/addons/web/views/webclient_templates.xml | head -8; echo =====; "
             "L=$(grep -n '<template id=\"login_layout\"' /opt/odoo20/addons/web/views/webclient_templates.xml | cut -d: -f1 | head -1); "
             "sed -n \"${L},$((L+45))p\" /opt/odoo20/addons/web/views/webclient_templates.xml",
             timeout=40, name='peek-login5')
print(out[:5000])
