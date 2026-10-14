#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""截图 BOM 入口（action-587）"""
import json
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

    for url in ['/odoo/action-587', '/odoo/587', '/odoo/mrp-bom']:
        try:
            page.goto(HOST + url, timeout=30000)
            page.wait_for_timeout(3500)
            rows = page.locator('table tbody tr').count()
            title = page.title()
            print('%s → HTTP OK, 行数 %d, %s' % (url, rows, title[:30]))
            if rows > 0:
                page.screenshot(path=f'{OUT}/bom_1_list.png')
                # 打开征途Pro BOM
                try:
                    page.click('text=BOM-ADK-H001', timeout=8000)
                    page.wait_for_timeout(3000)
                    page.screenshot(path=f'{OUT}/bom_2_detail.png')
                    page.evaluate('window.scrollTo(0, 600)')
                    page.wait_for_timeout(600)
                    page.screenshot(path=f'{OUT}/bom_3_ops.png')
                    print('详情截图 OK')
                except Exception as e:
                    print('详情失败:', str(e)[:80])
                break
        except Exception as e:
            print('%s → 失败: %s' % (url, str(e)[:60]))
    browser.close()
