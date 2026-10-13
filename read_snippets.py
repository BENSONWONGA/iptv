#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取关键 snippet XML 内容"""
import re
from bt_exec import BTExec

ex = BTExec()
out = ex.run("cat /opt/odoo20/addons/website/views/snippets/s_banner.xml | head -80; echo ===SPLIT===; "
             "ls /opt/odoo20/addons/website/views/snippets/ | grep -E 's_(three|numbers|text_image|text_block|features|call_to_action|title|columns|blockquote|product)' ; echo ===SPLIT===; "
             "ls /opt/odoo20/addons/website_sale/views/snippets/ 2>/dev/null; echo ===SPLIT===; "
             "find /opt/odoo20/addons/website_sale -name '*.xml' -path '*snippet*' | head -10",
             timeout=40, name='peek7')
print(out[:6000])
