#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复：创建独立模块 adk_website 承载 adk_outdoor.css，迁移 ir.asset 引用
（原引用挂在已卸载的 theme_liquid_glass 下导致登录页/前台 500）"""
import json
import time

import requests
from bt_exec import BTExec

HOST = 'http://220.162.99.166:9000'
ex = BTExec()
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:500])
    return d['result']


# ===== 1. 服务器上创建 adk_website 模块（直接 cp 已有 css，无需上传） =====
print('===== 1. 创建 adk_website 模块 =====')
out = ex.run(
    'mkdir -p /opt/odoo20/addons/adk_website/static/src/css /opt/odoo20/addons/adk_website/static/description && '
    'cp /opt/odoo20/addons/theme_liquid_glass/static/src/css/adk_outdoor.css /opt/odoo20/addons/adk_website/static/src/css/ && '
    'cp /opt/odoo20/addons/theme_liquid_glass/static/description/icon.png /opt/odoo20/addons/adk_website/static/description/ 2>/dev/null; '
    'touch /opt/odoo20/addons/adk_website/__init__.py && '
    'cat > /opt/odoo20/addons/adk_website/__manifest__.py << \'EOF\'\n'
    "{\n"
    "    'name': '奥登科品牌样式',\n"
    "    'version': '20.0.1.0.0',\n"
    "    'summary': 'ADK Outdoor 前端品牌样式（登录页分屏、首页等），独立于后端主题',\n"
    "    'category': 'Website',\n"
    "    'depends': ['website'],\n"
    "    'assets': {\n"
    "        'web.assets_frontend': [\n"
    "            'adk_website/static/src/css/adk_outdoor.css',\n"
    "        ],\n"
    "    },\n"
    "    'license': 'LGPL-3',\n"
    "}\n"
    'EOF\n'
    'chown -R odoo20:odoo20 /opt/odoo20/addons/adk_website && '
    'ls -la /opt/odoo20/addons/adk_website/ && echo MOD_OK',
    timeout=60, name='adk-fix')
print('模块创建:', 'OK' if 'MOD_OK' in out else out[-400:])
if 'MOD_OK' not in out:
    raise SystemExit(1)

# ===== 2. 重启 + 安装模块 =====
print('===== 2. 重启并安装 adk_website =====')
ex.run('systemctl restart odoo20', timeout=60, name='adk-fix')
time.sleep(12)
s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
rpc('ir.module.module', 'update_list')
mod = rpc('ir.module.module', 'search_read', [[['name', '=', 'adk_website']]], {'fields': ['name', 'state']})
print('模块识别:', mod)
if mod and mod[0]['state'] != 'installed':
    rpc('ir.module.module', 'button_immediate_install', [[mod[0]['id']]])
mod2 = rpc('ir.module.module', 'search_read', [[['name', '=', 'adk_website']]], {'fields': ['state']})
print('安装:', mod2[0]['state'])

# ===== 3. 迁移 ir.asset 引用 =====
print('===== 3. 迁移 ir.asset 引用 =====')
# 模块 manifest 自带 asset，先删旧记录避免重复加载
rpc('ir.asset', 'unlink', [[116]])
print('旧 ir.asset 116 (theme_liquid_glass/...adk_outdoor.css) 已删除')
# 确认新 asset 由模块安装自动生成
assets = rpc('ir.asset', 'search_read', [[['path', 'ilike', 'adk_outdoor.css']]], {'fields': ['name', 'bundle', 'path']})
print('当前 adk asset:', json.dumps(assets, ensure_ascii=False))
if not assets:
    # 模块安装未生成则手工补一条
    rpc('ir.asset', 'create', [{
        'name': 'adk_outdoor.css', 'bundle': 'web.assets_frontend',
        'directive': 'append', 'path': 'adk_website/static/src/css/adk_outdoor.css'}])
    print('已手工创建 ir.asset → adk_website/static/src/css/adk_outdoor.css')

# ===== 4. 清 bundle 缓存并验证 =====
print('===== 4. 清缓存并验证 =====')
atts = rpc('ir.attachment', 'search_read', [[['name', 'like', 'assets_']]], {'fields': ['name']})
to_del = [a['id'] for a in atts if a['name'].endswith(('.min.css', '.min.js'))]
if to_del:
    rpc('ir.attachment', 'unlink', [to_del])
    print('已删除 %d 个 bundle 附件' % len(to_del))
time.sleep(3)
for name, url in [('登录页', '/web/login'), ('前台首页', '/')]:
    r = s.get(HOST + url + '?t=%d' % time.time(), timeout=60)
    css_ok = 'adk' in r.text or 'adk_website' in r.text
    print('%s: HTTP %s, 长度 %d, 引用品牌样式: %s' % (name, r.status_code, len(r.text), '有' if css_ok else '无'))
print('===== 修复完成 =====')
