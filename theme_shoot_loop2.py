#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐主题安装 → Playwright(带登录态) 截图 → 卸载 v2"""
import json
import time

import requests
from playwright.sync_api import sync_playwright

HOST = 'http://220.162.99.166:9000'
DB = 'theme_demo'
ORDER = ['theme_kea', 'theme_loftspace', 'theme_treehouse', 'theme_enark',
         'theme_graphene', 'theme_bistro', 'theme_cobalt', 'theme_beauty',
         'theme_orchid', 'theme_nano', 'theme_avantgarde', 'theme_anelusia']
OUT = '/workspace/theme_previews'

s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=900):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:300])
    return d['result']


def login():
    r = s.post(HOST + '/web/session/authenticate', json={
        'jsonrpc': '2.0', 'params': {'db': DB, 'login': 'admin', 'password': 'Demo@2026'}}, timeout=120)
    uid = r.json().get('result', {}).get('uid')
    if not uid:
        raise RuntimeError('theme_demo 登录失败')
    return s.cookies.get('session_id')


def shoot(pw, theme, sid):
    fn = '%s/real_%s.png' % (OUT, theme)
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    ctx.add_cookies([{'name': 'session_id', 'value': sid,
                      'domain': '220.162.99.166', 'path': '/'}])
    page = ctx.new_page()
    url = HOST + '/?db=' + DB + '&t=%d' % time.time()
    page.goto(url, wait_until='networkidle', timeout=180000)
    page.wait_for_timeout(2500)
    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    page.wait_for_timeout(1500)
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_timeout(800)
    page.screenshot(path=fn, full_page=True)
    title = page.title()
    browser.close()
    return fn, title


sid = login()
print('session:', sid[:12], '...')

# 先清掉当前已装的演示主题
for m in rpc('ir.module.module', 'search_read',
             [[['state', '=', 'installed'], ['name', 'in', ORDER]]], {'fields': ['name']}) or []:
    print('清理已装主题:', m['name'])
    rpc('ir.module.module', 'button_immediate_uninstall', [[m['id']]])

pw = sync_playwright().start()
results = {}
for i, theme in enumerate(ORDER):
    keep = (i == len(ORDER) - 1)
    print('----- [%d/%d] %s %s -----' % (i + 1, len(ORDER), theme, '(保留)' if keep else ''))
    try:
        if i > 0:
            prev = ORDER[i - 1]
            pm = rpc('ir.module.module', 'search_read', [[['name', '=', prev]]], {'fields': ['state']})
            if pm and pm[0]['state'] == 'installed':
                print('  卸载 %s ...' % prev)
                rpc('ir.module.module', 'button_immediate_uninstall', [[pm[0]['id']]])
                time.sleep(2)
        m = rpc('ir.module.module', 'search_read', [[['name', '=', theme]]], {'fields': ['name', 'state']})
        if not m:
            results[theme] = 'not_found'
            print('  ✗ 未识别')
            continue
        if m[0]['state'] != 'installed':
            print('  安装中 ...')
            rpc('ir.module.module', 'button_immediate_install', [[m[0]['id']]])
        print('  截图 ...')
        fn, title = shoot(pw, theme, sid)
        results[theme] = 'ok'
        print('  ✓ %s | %s' % (fn.split('/')[-1], title[:40]))
    except Exception as e:
        results[theme] = 'error: %s' % str(e)[:150]
        print('  ✗ 异常:', str(e)[:200])
pw.stop()
print(json.dumps(results, ensure_ascii=False, indent=1))
ok = [k for k, v in results.items() if v == 'ok']
print('成功 %d/%d: %s' % (len(ok), len(ORDER), ', '.join(ok)))
