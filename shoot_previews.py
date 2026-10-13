#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对 12 个官方主题预览页(preview.html)截图"""
import time

from playwright.sync_api import sync_playwright

HOST = 'http://220.162.99.166:9000'
THEMES = ['theme_kea', 'theme_loftspace', 'theme_treehouse', 'theme_enark',
          'theme_graphene', 'theme_bistro', 'theme_cobalt', 'theme_beauty',
          'theme_orchid', 'theme_nano', 'theme_avantgarde', 'theme_anelusia']
OUT = '/workspace/theme_previews'

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    for t in THEMES:
        url = '%s/%s/static/description/preview.html' % (HOST, t)
        try:
            page.goto(url, wait_until='networkidle', timeout=120000)
            page.wait_for_timeout(2000)
            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            page.wait_for_timeout(1200)
            page.evaluate('window.scrollTo(0, 0)')
            page.wait_for_timeout(600)
            fn = '%s/preview_%s.png' % (OUT, t)
            page.screenshot(path=fn, full_page=True)
            h = page.evaluate('document.body.scrollHeight')
            print('%s: OK height=%dpx' % (t, h))
        except Exception as e:
            print('%s: FAIL %s' % (t, str(e)[:120]))
    browser.close()
print('done')
