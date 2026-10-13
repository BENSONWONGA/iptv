#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建汉化 inherit views（Add to Cart / 搜索框 / All products / Specifications）"""
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
        raise RuntimeError('%s/%s: %s' % (model, method, json.dumps(d['error'], ensure_ascii=False)[:400]))
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)


def view_id(key):
    v = rpc('ir.ui.view', 'search', [[['key', '=', key]]])
    if not v:
        raise SystemExit('view 不存在: %s' % key)
    return v[0]


def create_inherit(key, base_key, arch):
    exist = rpc('ir.ui.view', 'search', [[['key', '=', key]]])
    if exist:
        print('%s 已存在，跳过' % key)
        return
    rpc('ir.ui.view', 'create', [{
        'name': key, 'key': key, 'type': 'qweb',
        'inherit_id': view_id(base_key), 'arch_db': arch}])
    print('创建 %s (inherit %s) ✓' % (key, base_key))


# 1. 产品卡片"加入购物车"
create_inherit('adk_outdoor.cart_button_zh', 'website_sale.shop_product_buttons',
               '''<xpath expr="//button[@name='add_to_cart']/span[hasclass('o_label')]" position="replace">
    <span class="o_label small ms-1">加入购物车</span>
</xpath>''')

# 2. 搜索框 placeholder
create_inherit('adk_outdoor.searchbox_zh', 'website.website_search_box',
               '''<xpath expr="//input[@name='search']" position="attributes">
    <attribute name="t-att-placeholder">"搜索产品…"</attribute>
</xpath>''')

# 3. 商城无分类标题 All products → 全部商品；搜索结果文案
create_inherit('adk_outdoor.shop_title_zh', 'website_sale.products',
               '''<xpath expr="//div[hasclass('o_wsale_shop_title')]/h1" position="replace">
    <h1 class="h4-fs">全部商品</h1>
</xpath>''')

create_inherit('adk_outdoor.search_result_zh', 'website_sale.products',
               '''<xpath expr="//h1//span[hasclass('text-muted')][1]" position="replace">
    <span class="text-muted">搜索结果：</span>
</xpath>''')

# 4. 详情页面包屑 All products
create_inherit('adk_outdoor.breadcrumb_zh', 'website_sale.all_products_link_name',
               '''<xpath expr="//span" position="replace">
    <span placeholder="All products">全部商品</span>
</xpath>''')

# 5. 详情页 Specifications 标题
create_inherit('adk_outdoor.specs_zh', 'website_sale.product_attributes_body',
               '''<xpath expr="//h2[hasclass('m-0')]" position="replace">
    <h2 class="m-0 h3">规格参数</h2>
</xpath>''')

# 6. /shop 页面 title
pages = rpc('website.page', 'search_read', [[['url', '=', '/shop']]],
            {'fields': ['name', 'website_meta_title']})
print('/shop page:', pages)
if pages:
    rpc('website.page', 'write', [[pages[0]['id']], {'website_meta_title': '全部商品'}])
    print('/shop 页面标题已设置 ✓')

print('=== 汉化视图完成 ===')
