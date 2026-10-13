#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读 web.login_layout / web.login 基础模板"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run("grep -n 'template id=\"login\"\\|template id=\"login_layout\"' /opt/odoo20/addons/web/views/webclient_templates.xml; echo =====; "
             "awk '/<template id=\"login_layout\"/,/<\\/template>/' /opt/odoo20/addons/web/views/webclient_templates.xml | head -40; echo =====; "
             "awk '/<template id=\"login\" name/,/<\\/template>/' /opt/odoo20/addons/web/views/webclient_templates.xml | head -50",
             timeout=40, name='peek-login3')
print(out[:5000])
