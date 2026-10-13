#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诊断 theme_demo 首页重定向问题"""
import time

import requests

HOST = 'http://220.162.99.166:9000'

# 1. 匿名访问
r1 = requests.get(HOST + '/?db=theme_demo&t=%d' % time.time(), timeout=120, allow_redirects=False)
print('匿名 / : HTTP %s → Location: %s' % (r1.status_code, r1.headers.get('Location', '-')))

# 2. admin 登录态访问
s = requests.Session()
a = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'theme_demo', 'login': 'admin', 'password': 'Demo@2026'}}, timeout=120)
print('登录 uid:', a.json().get('result', {}).get('uid'))
r2 = s.get(HOST + '/?db=theme_demo&t=%d' % time.time(), timeout=120, allow_redirects=False)
print('admin / : HTTP %s → Location: %s | 长度 %d' % (r2.status_code, r2.headers.get('Location', '-'), len(r2.text)))
title = r2.text[r2.text.find('<title>'):r2.text.find('</title>')][:80] if '<title>' in r2.text else '-'
print('admin 页面 title:', title)


def rpc(model, method, args=None, kwargs=None, timeout=300):
    rr = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = rr.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:300])
    return d['result']


# 3. 网站与首页状态
sites = rpc('website', 'search_read', [[]], {'fields': ['name', 'homepage_url', 'domain']})
print('网站:', sites)
pages = rpc('website.page', 'search_read', [[['url', '=', '/'], ['website_id', '!=', False]]],
            {'fields': ['url', 'website_id', 'view_id', 'is_published']})
print('/ 页面记录:', [(p['url'], p['website_id'][1] if p['website_id'] else None,
                      p['is_published']) for p in pages])
hp = rpc('ir.ui.view', 'search_read', [[['key', '=', 'website.homepage']]],
         {'fields': ['id', 'key', 'website_id', 'arch_db']})
print('homepage 视图:', [(h['id'], h.get('website_id')) for h in hp], 'arch len:', [len(h.get('arch_db') or '') for h in hp])

# 4. 登录后跟随重定向看最终页面
r3 = s.get(HOST + '/?db=theme_demo&t=%d' % time.time(), timeout=120, allow_redirects=True)
print('admin / 跟随: final=%s len=%d' % (r3.url, len(r3.text)))
t2 = r3.text[r3.text.find('<title>'):r3.text.find('</title>')][:80] if '<title>' in r3.text else '-'
print('最终 title:', t2)
