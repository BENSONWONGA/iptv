#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""部署 DevsCodespace Backend Theme:
1. pg_dump 备份数据库
2. 卸载 theme_liquid_glass（避免后端主题冲突，文件保留可随时回装）
3. 分块上传 dcs zip → 解压到 addons
4. 重启 → 更新模块列表 → 安装
5. 清 bundle 缓存
"""
import base64
import json
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
ZIP = '/workspace/.uploads/4f33c544-fe78-4ced-b627-7576f76be783_dcs_backend_theme-20.0.1.0.0.zip'

ex = BTExec()
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=900):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


def login():
    s.post(HOST + '/web/session/authenticate', json={
        'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)


# ===== 1. 数据库备份 =====
print('===== 1. 备份数据库 =====')
stamp = time.strftime('%Y%m%d_%H%M%S')
bpath = '/opt/backups/benson_before_dcs_%s.sql.gz' % stamp
out = ex.run('mkdir -p /opt/backups && (sudo -u postgres pg_dump benson 2>/dev/null || pg_dump -U postgres benson) | gzip > %s && ls -la %s && echo BK_OK' % (bpath, bpath),
             timeout=300, name='dcs-deploy')
ok = 'BK_OK' in out
print('数据库备份:', 'OK → %s' % bpath if ok else out[-300:])
if not ok:
    raise SystemExit('备份失败，中止安装')

# ===== 2. 卸载 Liquid Glass =====
print('===== 2. 卸载 theme_liquid_glass =====')
login()
lg = rpc('ir.module.module', 'search_read', [[['name', '=', 'theme_liquid_glass']]], {'fields': ['name', 'state']})
if lg and lg[0]['state'] == 'installed':
    rpc('ir.module.module', 'button_immediate_uninstall', [[lg[0]['id']]])
    lg2 = rpc('ir.module.module', 'search_read', [[['name', '=', 'theme_liquid_glass']]], {'fields': ['state']})
    print('Liquid Glass:', lg[0]['state'], '→', lg2[0]['state'], '(文件保留在服务器，可随时回装)')
else:
    print('Liquid Glass 状态:', lg[0]['state'] if lg else '未找到，跳过')

# ===== 3. 上传 DCS =====
print('===== 3. 上传 dcs_backend_theme =====')
raw = open(ZIP, 'rb').read()
print('zip 大小: %.2f MB' % (len(raw) / 1048576))
b64 = base64.b64encode(raw).decode()
chunks = [b64[i:i + 60000] for i in range(0, len(b64), 60000)]
print('分 %d 块上传...' % len(chunks))
ex.run('rm -f /tmp/dcs.b64', timeout=15, name='dcs-deploy')
for i, c in enumerate(chunks):
    ex.run("echo -n %s >> /tmp/dcs.b64" % c, timeout=20, name='dcs-deploy')
    if (i + 1) % 20 == 0:
        print('  已上传 %d/%d' % (i + 1, len(chunks)))
out = ex.run(
    'base64 -d /tmp/dcs.b64 > /tmp/dcs.zip && cd /tmp && rm -rf dcs_backend_theme && unzip -q dcs.zip && '
    'rm -rf /opt/odoo20/addons/dcs_backend_theme && mv dcs_backend_theme /opt/odoo20/addons/ && '
    'chown -R odoo20:odoo20 /opt/odoo20/addons/dcs_backend_theme && rm -f /tmp/dcs.b64 /tmp/dcs.zip && '
    'ls /opt/odoo20/addons/dcs_backend_theme/ && echo UPLOAD_OK',
    timeout=120, name='dcs-deploy')
print('上传解压:', 'OK' if 'UPLOAD_OK' in out else out[-300:])
if 'UPLOAD_OK' not in out:
    raise SystemExit('上传失败')

# ===== 4. 重启 + 更新列表 + 安装 =====
print('===== 4. 重启 Odoo =====')
ex.run('systemctl restart odoo20', timeout=60, name='dcs-deploy')
time.sleep(12)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=30, name='dcs-deploy')
print('重启:', 'OK' if 'ACTIVE_OK' in out else out[-200:])

print('===== 5. 更新模块列表并安装 =====')
login()
rpc('ir.module.module', 'update_list')
dcs = rpc('ir.module.module', 'search_read', [[['name', '=', 'dcs_backend_theme']]], {'fields': ['name', 'state', 'latest_version']})
print('模块识别:', dcs)
if not dcs:
    raise SystemExit('未识别到模块，检查 addons 路径')
rpc('ir.module.module', 'button_immediate_install', [[dcs[0]['id']]])
dcs2 = rpc('ir.module.module', 'search_read', [[['name', '=', 'dcs_backend_theme']]], {'fields': ['state', 'latest_version']})
print('安装:', dcs[0]['state'], '→', dcs2[0]['state'], dcs2[0].get('latest_version'))

# ===== 6. 清 bundle 缓存 =====
print('===== 6. 清 bundle 缓存 =====')
login()
atts = rpc('ir.attachment', 'search_read', [[['name', 'like', 'web.assets_']]],
           {'fields': ['name']})
to_del = [a['id'] for a in atts if a['name'].endswith(('.min.css', '.min.js')) and 'frontend' not in a['name']]
if to_del:
    rpc('ir.attachment', 'unlink', [to_del])
print('已删除 %d 个后端 bundle 附件' % len(to_del))

print('===== 部署完成，可进行浏览器验收 =====')
