# -*- coding: utf-8 -*-
import json
from playwright.sync_api import sync_playwright

CHROME = '/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome'
BASE = 'http://220.162.99.166:88/odk'
bad = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send('Network.enable')
    cdp.send('Network.setCacheDisabled', {'cacheDisabled': True})
    page.on('response', lambda r: bad.append({'url': r.url, 'status': r.status}) if r.status >= 400 else None)
    page.goto(BASE, wait_until='domcontentloaded', timeout=60000)
    page.wait_for_timeout(3000)
    browser.close()
print('HTTP>=400 responses:')
print(json.dumps(bad, ensure_ascii=False, indent=1))
