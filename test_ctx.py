#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 context 传法：让 server action 的 records 生效"""
import json
import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'

s = requests.Session()

r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']


def rpc(endpoint, params):
    r = s.post(HOST + endpoint, json={'jsonrpc': '2.0', 'method': 'call', 'params': params}, timeout=120)
    d = r.json()
    if 'error' in d:
        return {'__error': d['error'].get('data', {}).get('message', str(d['error']))[:200]}
    return d.get('result')


# 建一张检验单 + 找 action
insp = rpc('/web/dataset/call_kw', {
    'model': 'x_qc_inspection', 'method': 'create',
    'args': [{'x_inspection_type': 'oqc', 'x_product_id': rpc('/web/dataset/call_kw', {
        'model': 'product.product', 'method': 'search',
        'args': [[['default_code', '=', 'FG-SHO-042']]]})[0], 'x_qty': 10}],
}) if False else None

shoe = rpc('/web/dataset/call_kw', {
    'model': 'product.product', 'method': 'search',
    'args': [[['default_code', '=', 'FG-SHO-042']]], 'kwargs': {}})
print('shoe 搜索结果:', shoe)
if not isinstance(shoe, list) or not shoe:
    raise SystemExit('搜索失败')
shoe = shoe[0]
insp = rpc('/web/dataset/call_kw', {
    'model': 'x_qc_inspection', 'method': 'create',
    'args': [{'x_inspection_type': 'oqc', 'x_product_id': shoe, 'x_qty': 10}]})
print('检验单:', insp)

act = rpc('/web/dataset/call_kw', {
    'model': 'ir.actions.server', 'method': 'search',
    'args': [[['name', '=', '检验单：开始检验']]], 'kwargs': {}})[0]
print('action:', act)

CTX = {'lang': 'zh_CN', 'tz': 'Asia/Shanghai', 'uid': uid,
       'active_id': insp, 'active_ids': [insp], 'active_model': 'x_qc_inspection'}

# 变体 A: kwargs.context
rA = rpc('/web/dataset/call_kw', {
    'model': 'ir.actions.server', 'method': 'run',
    'args': [[act]], 'kwargs': {'context': CTX}})
print('A kwargs.context =>', rA)

# 变体 B: context 作为 args 最后位置参数
rB = rpc('/web/dataset/call_kw', {
    'model': 'ir.actions.server', 'method': 'run',
    'args': [[act], CTX]})
print('B args 尾部 =>', rB)

# 变体 C: call_button
rC = rpc('/web/dataset/call_button', {
    'model': 'ir.actions.server', 'method': 'run',
    'args': [[act]], 'kwargs': {'context': CTX}})
print('C call_button =>', str(rC)[:150])

# 查状态
st = rpc('/web/dataset/call_kw', {
    'model': 'x_qc_inspection', 'method': 'read',
    'args': [[insp]], 'kwargs': {'fields': ['x_state', 'x_name'], 'context': {'lang': 'zh_CN'}}})
print('状态:', st)

# 清理
rpc('/web/dataset/call_kw', {'model': 'x_qc_inspection', 'method': 'unlink',
                             'args': [[insp]], 'kwargs': {}})
print('已清理')
