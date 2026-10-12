#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 liquid glass 主题追加瑕疵修复 CSS → 重启 → 升级"""
import time

from bt_exec import BTExec

PATCH = r'''

/* ===== ShoeFactory 补丁：瑕疵修复 ===== */
/* 1. 列表表头文字白色（原为黑色，深底上对比不足） */
.o_list_renderer thead th,
table.o_list_table thead th,
.o_list_view thead th {
    color: #ffffff !important;
}
/* 2. 可选列切换按钮（tune 图标）白色 */
.o_control_panel .o_optional_columns_dropdown_toggle,
.o_cp_buttons .btn .fa,
.o_cp_buttons .btn .oi {
    color: #ffffff !important;
}
/* 3. 展开的搜索输入区玻璃底 */
.o_control_panel .o_searchview_container .o_searchview_input_container,
.o_control_panel .o_searchview_more,
.o_searchview .o_searchview_input {
    background: transparent;
}
.o_searchview {
    background: rgba(255, 255, 255, 0.10) !important;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 12px !important;
}
'''

ex = BTExec()
b64 = __import__('base64').b64encode(PATCH.encode()).decode()
cmd = ("echo -n %s | base64 -d >> /opt/odoo20/addons/theme_liquid_glass/static/src/scss/glass_theme.scss && "
       "tail -5 /opt/odoo20/addons/theme_liquid_glass/static/src/scss/glass_theme.scss && echo PATCH_OK" % b64)
out = ex.run(cmd, timeout=20, name='lg-patch')
print('PATCH_OK ✓' if 'PATCH_OK' in out else out)

ex.run('systemctl restart odoo20', timeout=30, name='lg-patch')
time.sleep(9)
out = ex.run('systemctl is-active odoo20 && echo ACTIVE_OK', timeout=20, name='lg-patch')
print('重启 ✓' if 'ACTIVE_OK' in out else out)

# 升级模块重建资产
import json
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()
r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
uid = r.json()['result']['uid']


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=600)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:300])
    return d['result']


ids = rpc('ir.module.module', 'search', [[['name', '=', 'theme_liquid_glass']]])
rpc('ir.module.module', 'button_immediate_upgrade', [ids])

# 验证补丁进了 scss 文件
r = s.get(HOST + '/theme_liquid_glass/static/src/scss/glass_theme.scss', params={'_t': '9'}, timeout=30)
ok = 'ShoeFactory 补丁' in r.content.decode()
print('补丁已生效 ✓' if ok else '补丁未生效!', '(%d 字节)' % len(r.content))
