#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐主题安装 → Playwright 截图 → 卸载，在 theme_demo 库上轮询 12 个官方主题。
最后一个主题（anelusia）保留安装，供用户在线浏览。"""
import json
import time

import requests
from playwright.sync_api import sync_playwright

HOST = 'http://220.162.99.166:9000'
DB = 'theme_demo'
# anelusia 与户外鞋最契合，放最后保留安装
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
    return uid


def shoot(pw, theme):
    """截图主题首页（全页）"""
    fn = '%s/real_%s.png' % (OUT, theme)
    browser = pw.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    url = HOST + '/?db=' + DB + '&t=%d' % time.time()
    page.goto(url, wait_until='networkidle', timeout=180000)
    page.wait_for_timeout(3000)
    # 滚到底部触发懒加载后再全页截图
    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    page.wait_for_timeout(1500)
    page.evaluate('window.scrollTo(0, 0)')
    page.wait_for_timeout(800)
    page.screenshot(path=fn, full_page=True)
    title = page.title()
    browser.close()
    return fn, title


login()
pw = sync_playwright().start()
results = {}
for i, theme in enumerate(ORDER):
    keep = (i == len(ORDER) - 1)
    print('----- [%d/%d] %s %s -----' % (i + 1, len(ORDER), theme, '(保留)' if keep else ''))
    try:
        # 卸载上一个（非保留）
        if i > 0:
            prev = ORDER[i - 1]
            pm = rpc('ir.module.module', 'search_read', [[['name', '=', prev]]], {'fields': ['state']})
            if pm and pm[0]['state'] == 'installed':
                print('  卸载 %s ...' % prev)
                rpc('ir.module.module', 'button_immediate_uninstall', [[pm[0]['id']]])
                time.sleep(2)
        # 安装当前
        m = rpc('ir.module.module', 'search_read', [[['name', '=', theme]]], {'fields': ['name', 'state']})
        if not m:
            print('  ✗ 模块未识别'); results[theme] = 'not_found'; continue
        if m[0]['state'] != 'installed':
            print('  安装中 ...')
            rpc('ir.module.module', 'button_immediate_install', [[m[0]['id']]])
        print('  安装完成，截图 ...')
        fn, title = shoot(pw, theme)
        results[theme] = 'ok'
        print('  ✓ %s | title=%s' % (fn.split('/')[-1], title[:50]))
    except Exception as e:
        results[theme] = 'error: %s' % str(e)[:150]
        print('  ✗ 异常:', str(e)[:200])
pw.stop()
print(json.dumps(results, ensure_ascii=False, indent=1))
ok = [k for k, v in results.items() if v == 'ok']
print('成功 %d/%d: %s' % (len(ok), len(ORDER), ', '.join(ok)))
