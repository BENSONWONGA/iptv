#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包 shoe_theme → 分块上传宝塔 → 解压安装"""
import base64
import os
import subprocess
import sys
import time
import zipfile

THEME_DIR = '/workspace/shoe_theme'
ZIP_PATH = '/workspace/shoe_theme.zip'

# 1. 打包（用 python zipfile，保证路径结构 shoe_theme/...）
if os.path.exists(ZIP_PATH):
    os.remove(ZIP_PATH)
with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(THEME_DIR):
        for f in files:
            full = os.path.join(root, f)
            arc = os.path.join('shoe_theme', os.path.relpath(full, THEME_DIR))
            zf.write(full, arc)
size = os.path.getsize(ZIP_PATH)
print('打包完成: %d 字节' % size)

# 2. 分块上传
from bt_exec import BTExec

ex = BTExec()
b64 = base64.b64encode(open(ZIP_PATH, 'rb').read()).decode()
CHUNK = 30000
chunks = [b64[i:i + CHUNK] for i in range(0, len(b64), CHUNK)]
print('分 %d 块上传...' % len(chunks))

# 清理旧临时文件
print(ex.run('rm -f /tmp/st.b64 /tmp/shoe_theme.zip; rm -rf /opt/odoo20/addons/shoe_theme', timeout=15, name='theme-deploy'))
for i, c in enumerate(chunks):
    out = ex.run("echo -n %s >> /tmp/st.b64" % c, timeout=15, name='theme-deploy')
    if 'Successful' not in out:
        print('块 %d 异常: %s' % (i, out[:200]))
        sys.exit(1)
print('上传完成')

# 3. 解码 + 解压 + 权限
cmd = ('base64 -d /tmp/st.b64 > /tmp/shoe_theme.zip && '
       'cd /opt/odoo20/addons && unzip -oq /tmp/shoe_theme.zip && '
       'chown -R odoo20:odoo20 /opt/odoo20/addons/shoe_theme && '
       'ls -la /opt/odoo20/addons/shoe_theme/ && '
       'rm -f /tmp/st.b64 /tmp/shoe_theme.zip && echo DEPLOY_OK')
out = ex.run(cmd, timeout=30, name='theme-deploy')
print(out)
if 'DEPLOY_OK' not in out:
    sys.exit('解压失败')

# 4. 重启 Odoo
out = ex.run('systemctl restart odoo20 && sleep 3 && systemctl is-active odoo20 && echo RESTART_OK',
             timeout=40, name='theme-deploy')
print(out)
if 'RESTART_OK' not in out:
    sys.exit('重启失败')
print('=== 模块已部署并重启 Odoo ===')
