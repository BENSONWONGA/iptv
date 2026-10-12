#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重现 unhashable 错误并获取完整 traceback"""
import json
import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'

s = requests.Session()

r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']

shoe = s.post(HOST + '/web/dataset/call_kw', json={
    'jsonrpc': '2.0', 'method': 'call',
    'params': {'model': 'product.product', 'method': 'search',
               'args': [[['default_code', '=', 'FG-SHO-042']]], 'kwargs': {}}}, timeout=60).json()['result'][0]

insp = s.post(HOST + '/web/dataset/call_kw', json={
    'jsonrpc': '2.0', 'method': 'call',
    'params': {'model': 'x_qc_inspection', 'method': 'create',
               'args': [{'x_inspection_type': 'oqc', 'x_product_id': shoe, 'x_qty': 10}],
               'kwargs': {}}}, timeout=60).json()['result']
print('insp:', insp)

act = s.post(HOST + '/web/dataset/call_kw', json={
    'jsonrpc': '2.0', 'method': 'call',
    'params': {'model': 'ir.actions.server', 'method': 'search',
               'args': [[['name', '=', '检验单：开始检验']]], 'kwargs': {}}}, timeout=60).json()['result'][0]

CTX = {'lang': 'zh_CN', 'tz': 'Asia/Shanghai', 'uid': uid,
       'active_id': insp, 'active_ids': [insp], 'active_model': 'x_qc_inspection'}

r = s.post(HOST + '/web/dataset/call_kw', json={
    'jsonrpc': '2.0', 'method': 'call',
    'params': {'model': 'ir.actions.server', 'method': 'run',
               'args': [[act]], 'kwargs': {'context': CTX}}}, timeout=120)
d = r.json()
if 'error' in d:
    dbg = d['error'].get('data', {}).get('debug', '')
    print('=== ERROR ===')
    print(dbg[:2500])
else:
    print('OK:', d['result'])

# 清理
s.post(HOST + '/web/dataset/call_kw', json={
    'jsonrpc': '2.0', 'method': 'call',
    'params': {'model': 'x_qc_inspection', 'method': 'unlink',
               'args': [[insp]], 'kwargs': {}}}, timeout=60)
