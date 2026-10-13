#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试服务器到 GitHub 的连通性"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run(
    'timeout 20 curl -sSI https://raw.githubusercontent.com/odoo/design-themes/20.0/theme_kea/__manifest__.py 2>&1 | head -3; echo ---GIT---; '
    'timeout 30 git ls-remote --heads https://github.com/odoo/design-themes.git 2>&1 | head -3; echo ---Codeload---; '
    'timeout 20 curl -sSI https://codeload.github.com/odoo/design-themes/tar.gz/refs/heads/20.0 2>&1 | head -3',
    timeout=90, name='gh-test')
print(out)
