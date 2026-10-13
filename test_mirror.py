#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试镜像下载速度：各下载 5MB 测速"""
from bt_exec import BTExec

ex = BTExec()
out = ex.run(
    'cd /tmp && for u in "https://ghfast.top/https://github.com/odoo/design-themes/archive/refs/heads/20.0.tar.gz" '
    '"https://mirror.ghproxy.com/https://github.com/odoo/design-themes/archive/refs/heads/20.0.tar.gz" '
    '"https://ghproxy.net/https://github.com/odoo/design-themes/archive/refs/heads/20.0.tar.gz"; do '
    'echo "== $u"; timeout 25 curl -sSL -m 20 -r 0-5242880 -o t.bin -w "  speed=%{speed_download} B/s http=%{http_code}\\n" "$u" 2>&1 | tail -1; done; rm -f t.bin',
    timeout=120, name='mirror-test')
print(out)
