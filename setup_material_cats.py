#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按用户架构图建材料分类树：材料总表 → 皮料/革料/布料/辅料/材料委外/针辅/包装类/底料/刀模制具/化学品/消耗品，并迁移现有物料"""
import requests

HOST = 'http://220.162.99.166:9000'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=300)
    d = r.json()
    if 'error' in d:
        raise RuntimeError(str(d['error'])[:400])
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': 'benson', 'login': 'admin', 'password': 'Benson@2026'}}, timeout=60)
print('登录 ✓')

# ── 1. 建分类树（幂等：已存在则跳过）──────────────
existing = {c['name']: c['id'] for c in rpc('product.category', 'search_read', kwargs={'fields': ['name'], 'limit': 200})}

ROOT = '材料总表'
SUBS = ['皮料', '革料', '布料', '辅料', '材料委外', '针辅', '包装类', '底料', '刀模制具', '化学品', '消耗品']

if ROOT not in existing:
    existing[ROOT] = rpc('product.category', 'create', [{'name': ROOT}])
    print('建父分类: %s (id=%s)' % (ROOT, existing[ROOT]))
else:
    print('父分类已存在: %s' % ROOT)

for name in SUBS:
    if name in existing:
        print('  子分类已存在: %s' % name)
        continue
    existing[name] = rpc('product.category', 'create', [{'name': name, 'parent_id': existing[ROOT]}])
    print('  建子分类: %s (id=%s)' % (name, existing[name]))

# ── 2. 迁移现有物料到新分类 ───────────────────────
MIGRATE = {
    '头层牛皮-黑色': '皮料',
    '针织内里布-黑色': '布料',
    'EVA中底-男休闲款': '底料',
    '橡胶大底-男休闲款': '底料',
    '乳胶鞋垫-男款': '辅料',
    '圆头鞋带-黑-120cm': '辅料',
    '涤纶缝纫线-黑': '针辅',
    '环保水性胶水': '化学品',
    '鞋楦-男休闲42码': '刀模制具',
    '外箱-双层瓦楞': '包装类',
    '鞋盒-男休闲款': '包装类',
    # 男士休闲皮鞋留在 成品鞋
}
for pname, cname in MIGRATE.items():
    ids = rpc('product.template', 'search', kwargs={'domain': [['name', '=', pname]]})
    if not ids:
        print('  ✗ 未找到产品: %s' % pname)
        continue
    rpc('product.template', 'write', [ids, {'categ_id': existing[cname]}])
    print('  %s → %s ✓' % (pname, cname))

# ── 3. 删除空旧分类（面料/底材/辅料/包装材料）─────
for old in ['面料', '底材', '辅料', '包装材料']:
    ids = rpc('product.category', 'search', kwargs={'domain': [['name', '=', old]]})
    if not ids:
        print('  旧分类 %s 不存在' % old)
        continue
    cnt = rpc('product.template', 'search_count', kwargs={'domain': [['categ_id', 'in', ids]]})
    if cnt:
        print('  ✗ %s 下仍有 %d 个产品，跳过删除' % (old, cnt))
        continue
    rpc('product.category', 'unlink', [ids])
    print('  删除旧分类: %s ✓' % old)

# ── 4. 验证 ─────────────────────────────────────
cats = rpc('product.category', 'search_read', kwargs={
    'domain': [['name', 'in', [ROOT] + SUBS + ['成品鞋', '半成品']]],
    'fields': ['name', 'parent_id'], 'limit': 50})
print('\n=== 最终分类树 ===')
by_id = {c['id']: c for c in cats}
for c in sorted(cats, key=lambda x: (x['parent_id'] is None, x['name'])):
    p = c['parent_id'][1] if c['parent_id'] else '-'
    print('  %s (父:%s)' % (c['name'], p))

prods = rpc('product.template', 'search_read', kwargs={'domain': [['categ_id', '!=', False]], 'fields': ['name', 'categ_id'], 'limit': 100})
print('\n=== 物料归属 ===')
for p in prods:
    print('  %s → %s' % (p['name'], p['categ_id'][1]))
print('\n完成 ✓')
