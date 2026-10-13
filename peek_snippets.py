#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看服务器上 Odoo 20 网站代码块(snippet)源码结构"""
from bt_exec import BTExec

ex = BTExec()

# 找 snippet 模板文件
out = ex.run("ls /opt/odoo20/odoo/addons/website/static/src/snippets/ 2>/dev/null | head -40; "
             "ls /opt/odoo20/odoo/addons/website/views/ 2>/dev/null | head -20; "
             "grep -l 's_banner' /opt/odoo20/odoo/addons/website/views/*.xml 2>/dev/null",
             timeout=30, name='peek1')
print('=== 网站模块 snippet 位置 ===')
print(out)

# 查看 s_banner 定义
out2 = ex.run("grep -rn 'template id=\"s_banner\"' /opt/odoo20/odoo/addons/website/ 2>/dev/null | head -5; "
              "find /opt/odoo20/odoo/addons/website -name '*.xml' -path '*snippet*' 2>/dev/null | head -20",
              timeout=30, name='peek2')
print('=== s_banner 定义位置 ===')
print(out2)
