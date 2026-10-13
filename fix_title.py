#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 /shop 页面标题"""
import json

import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(json.dumps(d['error'], ensure_ascii=False)[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)

key = 'adk_outdoor.shop_title_var'
exist = rpc('ir.ui.view', 'search', [[['key', '=', key]]])
if not exist:
    base = rpc('ir.ui.view', 'search', [[['key', '=', 'website_sale.products']]])[0]
    rpc('ir.ui.view', 'create', [{
        'name': key, 'key': key, 'type': 'qweb', 'inherit_id': base,
        'arch_db': '''<xpath expr="//t[@t-call='website.layout']" position="attributes">
    <attribute name="additional_title">category.name if category else '全部商品'</attribute>
</xpath>'''}])
    print('shop 标题视图已创建 ✓')
else:
    print('已存在')

# 验证
import time
time.sleep(2)
r = requests.get(HOST + '/shop', timeout=60)
import re
m = re.search(r'<title>(.*?)</title>', r.text)
print('/shop title:', m.group(1))
r2 = requests.get(HOST + '/shop?category=1', timeout=60)
m2 = re.search(r'<title>(.*?)</title>', r2.text)
print('/shop?category=1 title:', m2.group(1))
h = r.text
print('加入购物车:', h.count('加入购物车'), '| Add to Cart:', h.count('Add to Cart'))
print('搜索产品…:', h.count('搜索产品…'), '| Search...:', h.count('Search...'))
