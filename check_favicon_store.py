#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""确认 website.favicon 的底层存储（ir.attachment or 字段列）"""
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=120)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:300])
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
print('uid =', r.json()['result']['uid'])

atts = rpc('ir.attachment', 'search_read', [[
    ['res_model', '=', 'website'], ['res_id', '=', 1], ['res_field', '=', 'favicon']
], ['id', 'name', 'res_field', 'mimetype', 'file_size']])
print('website favicon attachments:', atts)

# 顺带看 company logo 的存储方式
atts2 = rpc('ir.attachment', 'search_read', [[
    ['res_model', '=', 'res.company'], ['res_id', '=', 1], ['res_field', '=', 'logo']
], ['id', 'name', 'mimetype', 'file_size']])
print('company logo attachments:', atts2)
