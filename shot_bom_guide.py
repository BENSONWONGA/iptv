#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""截图 BOM 入口路径：菜单 → BOM 列表 → BOM 详情（组件+工序）"""
import json
import re
import urllib.request

from playwright.sync_api import sync_playwright

HOST = 'http://220.162.99.166:9000'
OUT = '/workspace/theme_previews'

req = urllib.request.Request(
    HOST + '/web/session/authenticate',
    data=json.dumps({'jsonrpc': '2.0', 'params': {
        'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}).encode(),
    headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req, timeout=60)
sid = resp.headers.get('Set-Cookie', '').split('session_id=')[1].split(';')[0]

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    ctx.add_cookies([{'name': 'session_id', 'value': sid,
                      'domain': '220.162.99.166', 'path': '/'}])
    page = ctx.new_page()

    # 1. BOM 列表页（直接菜单 URL：制造→产品→物料清单）
    page.goto(HOST + '/odoo/mrp-bom?t=1', timeout=60000)
    page.wait_for_timeout(4000)
    rows = page.locator('table tbody tr').count()
    print('BOM 列表行数:', rows)
    page.screenshot(path=f'{OUT}/bom_1_list.png')

    # 展开左侧菜单树（制造 → 产品），露出「物料清单」菜单项
    try:
        # 点制造应用菜单
        page.click('text=制造', timeout=5000)
        page.wait_for_timeout(1000)
    except Exception:
        pass
    page.screenshot(path=f'{OUT}/bom_2_menu.png', full_page=False)

    # 2. 打开一个 BOM 详情（征途Pro）
    page.goto(HOST + '/odoo/mrp-bom?t=2', timeout=60000)
    page.wait_for_timeout(3000)
    try:
        page.click('text=BOM-ADK-H001', timeout=8000)
        page.wait_for_timeout(3500)
        page.screenshot(path=f'{OUT}/bom_3_detail.png')
        # 滚到工序区
        page.evaluate('window.scrollTo(0, 700)')
        page.wait_for_timeout(800)
        page.screenshot(path=f'{OUT}/bom_4_ops.png')
        # 抓组件行数
        comps = page.locator('.o_list_table tbody tr, table tbody tr').count()
        print('详情页表格行(组件+工序):', comps)
    except Exception as e:
        print('打开详情失败:', str(e)[:100])

    # 3. 物料（材料产品）列表：制造→产品→产品 里筛材料
    page.goto(HOST + '/odoo/products?t=3', timeout=60000)
    page.wait_for_timeout(4000)
    rows = page.locator('table tbody tr').count()
    print('产品列表行数:', rows)
    page.screenshot(path=f'{OUT}/bom_5_products.png')
    browser.close()
print('截图完成')
