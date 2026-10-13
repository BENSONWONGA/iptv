#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""奥登科户外：网站设置 + 首页定制 + 菜单 + 品牌CSS"""
import base64
import json
import time

import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'
ASSETS = '/workspace/site_assets'
LOGO = '/workspace/.uploads/31c555f2-339a-4f75-b82b-03028e55105b_奥登科logops.png'
CSS_LOCAL = '/workspace/adk_outdoor.css'
CSS_REMOTE = '/opt/odoo20/addons/theme_liquid_glass/static/src/css/adk_outdoor.css'

DATA = json.load(open('/workspace/outdoor_data.json'))
CAT_IDS = DATA['cat_ids']  # name -> id

s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}},
    }, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError('%s/%s: %s' % (model, method, json.dumps(d['error'], ensure_ascii=False)[:400]))
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']
print('RPC 登录 ✓')

# ---------- 0. 货币 ----------
cur = rpc('res.company', 'read', [[1]], {'fields': ['currency_id']})[0]['currency_id']
cur_sym = rpc('res.currency', 'read', [[cur[0]]], {'fields': ['symbol']})[0]['symbol']
print('公司货币:', cur[1], cur_sym)


def price_str(v):
    return '%s %s' % (cur_sym, int(v) if v == int(v) else v)


# ---------- 1. 公共图片附件（hero / 品牌故事） ----------
def public_attachment(name, path, max_side=1600):
    exist = rpc('ir.attachment', 'search', [[('name', '=', name), ('res_model', '=', False)]])
    if exist:
        return exist[0]
    import io
    from PIL import Image
    im = Image.open(path).convert('RGB')
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return rpc('ir.attachment', 'create', [{
        'name': name, 'datas': b64, 'public': True, 'mimetype': 'image/jpeg',
        'description': '奥登科户外网站素材'}])


hero_id = public_attachment('adk_hero_mountain.jpg', '%s/hero_mountain.jpg' % ASSETS, 1600)
brand_id = public_attachment('adk_brand_story.jpg', '%s/brand_story.jpg' % ASSETS, 1400)
print('hero 附件:', hero_id, '| brand 附件:', brand_id)

# ---------- 2. 网站设置 ----------
logo_b64 = base64.b64encode(open(LOGO, 'rb').read()).decode()
rpc('website', 'write', [[1], {
    'name': '奥登科户外 AUDENKO OUTDOOR',
    'logo': logo_b64,
}])
print('网站名称/Logo 已更新 ✓')

# ---------- 3. 产品信息（用于首页卡片） ----------
prod_ids = [p['id'] for p in DATA['products']]
prods = rpc('product.template', 'read', [prod_ids],
            {'fields': ['name', 'list_price', 'website_url', 'public_categ_ids', 'website_sequence']})
prods_by_id = {p['id']: p for p in prods}
cat_names = {v: k for k, v in CAT_IDS.items()}
for p in prods:
    p['cat_name'] = cat_names.get(p['public_categ_ids'][0], '') if p['public_categ_ids'] else ''

FEATURED = [25, 29, 32, 26, 31, 33, 28, 35]  # 征途Pro/猎鹰/巅峰8000/岚风/疾风/极地/铁途/溯溪者


def product_card(pid):
    p = prods_by_id[pid]
    return ('<div class="col-6 col-md-4 col-lg-3 pt16 pb16">\n'
            '  <a href="{url}" class="adk-card d-block text-decoration-none">\n'
            '    <div class="overflow-hidden rounded-top shadow-sm">\n'
            '      <img src="/web/image/product.template/{pid}/image_1920" class="img img-fluid w-100 adk-card-img" alt="{name}" loading="lazy"/>\n'
            '    </div>\n'
            '    <div class="bg-white border border-top-0 rounded-bottom p-3 text-center adk-card-body">\n'
            '      <p class="small text-muted mb-1">{cat}</p>\n'
            '      <h5 class="h6-fs fw-bold mb-1">{name}</h5>\n'
            '      <p class="fw-bold mb-0 text-primary">{price}</p>\n'
            '    </div>\n'
            '  </a>\n'
            '</div>').format(url=p['website_url'], pid=pid, name=p['name'],
                             cat=p['cat_name'], price=price_str(p['list_price']))


def cat_card(title, count, img_pid, href, img_static=None):
    img = img_static or ('/web/image/product.template/%d/image_1920' % img_pid)
    return ('<div class="col-6 col-lg-3 pt16 pb16">\n'
            '  <a href="{href}" class="adk-card d-block text-decoration-none">\n'
            '    <div class="overflow-hidden rounded shadow-sm position-relative">\n'
            '      <img src="{img}" class="img img-fluid w-100 adk-card-img" alt="{title}" loading="lazy"/>\n'
            '      <div class="position-absolute top-0 start-0 w-100 h-100" style="background: linear-gradient(to top, rgba(0,0,0,.55), rgba(0,0,0,0) 55%);"/>\n'
            '      <div class="position-absolute bottom-0 start-0 w-100 text-white p-3">\n'
            '        <h5 class="h5-fs fw-bold mb-0">{title}</h5>\n'
            '        <p class="small mb-0 opacity-75">{count}</p>\n'
            '      </div>\n'
            '    </div>\n'
            '  </a>\n'
            '</div>').format(href=href, img=img, title=title, count=count)


cat_cards = (
    cat_card('徒步系列', '4 款产品 · 轻装到重装', 25, '/shop?category=%d' % CAT_IDS['徒步系列'])
    + cat_card('越野跑系列', '3 款产品 · 竞速与缓震', 29, '/shop?category=%d' % CAT_IDS['越野跑系列'])
    + cat_card('登山系列', '3 款产品 · 雪山与岩壁', 32, '/shop?category=%d' % CAT_IDS['登山系列'])
    + cat_card('全部装备', '12 款产品 · 全系列', 35, '/shop')
)
featured_cards = '\n'.join(product_card(pid) for pid in FEATURED)

ARCH = '''<t name="Homepage" t-name="website.homepage">
    <t t-call="website.layout">
        <t t-set="pageName" t-value="'homepage'"/>
        <div id="wrap">
            <section class="s_banner o_half_screen_height d-flex align-items-center oe_img_bg o_bg_img_center oe_custom_bg" style="background-image: url('/web/image/{hero_id}');" data-name="Banner" data-snippet="s_banner">
                <div class="o_we_bg_filter bg-black-50"/>
                <div class="container">
                    <div class="row">
                        <div class="col-lg-8 pt56 pb56 text-white">
                            <p class="mb-2 fw-bold" style="letter-spacing: .35em; font-size: .9rem;">AUDENKO OUTDOOR · 奥登科户外</p>
                            <h1 class="display-3 fw-bolder">山野之履，始于足下</h1>
                            <p class="lead mt-3 mb-4" style="max-width: 34rem;">源自"中国鞋都"晋江，25 年制鞋工艺沉淀。防水、防滑、耐穿 —— 为每一次远征打造可靠战靴。</p>
                            <p class="mb-0">
                                <a href="/shop" class="btn btn-lg btn-primary me-2">选购全系列</a>
                                <a href="#series" class="btn btn-lg btn-outline-light">探索装备</a>
                            </p>
                        </div>
                    </div>
                </div>
            </section>
            <section class="pt80 pb80" id="series" data-name="系列导航" data-snippet="s_features">
                <div class="container">
                    <div class="row pb24">
                        <div class="col-lg-8 offset-lg-2 text-center pt16 pb16">
                            <h2 class="fw-bold">探索系列</h2>
                            <p class="lead">从轻装快行到高海拔远征，总有一双适合你的下一个目标</p>
                        </div>
                    </div>
                    <div class="row">
                        {cat_cards}
                    </div>
                </div>
            </section>
            <section class="pt80 pb80 bg-light" data-name="本季精选" data-snippet="s_products">
                <div class="container">
                    <div class="row align-items-end pb24">
                        <div class="col-lg-8 pt16 pb16">
                            <h2 class="fw-bold">本季精选</h2>
                            <p class="lead">编辑部实测推荐，覆盖徒步、越野跑与高山场景</p>
                        </div>
                        <div class="col-lg-4 text-lg-end pt16 pb16">
                            <a href="/shop" class="btn btn-secondary">查看全部产品 <span class="oi ms-1" data-icon="keyboard_arrow_right" role="img"/></a>
                        </div>
                    </div>
                    <div class="row">
                        {featured_cards}
                    </div>
                </div>
            </section>
            <section class="pt80 pb80" data-name="三大科技" data-snippet="s_features">
                <div class="container">
                    <div class="row pb24">
                        <div class="col-lg-8 offset-lg-2 text-center pt16 pb16">
                            <h2 class="fw-bold">奥登科户外科技</h2>
                            <p class="lead">每一代产品，都是向山野更近一步的迭代</p>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-lg-4 text-center pt16 pb16">
                            <p class="display-5 fw-bolder text-primary mb-2">AK-TEX</p>
                            <h4 class="h5-fs fw-bold">防水透气科技</h4>
                            <p class="text-muted">自主研发防水透气膜，静水压 10000mm，透湿量 5000g/m²·24h，风雨中保持足部干爽。</p>
                        </div>
                        <div class="col-lg-4 text-center pt16 pb16">
                            <p class="display-5 fw-bolder text-primary mb-2">GRIP·X</p>
                            <h4 class="h5-fs fw-bold">魔爪耐磨大底</h4>
                            <p class="text-muted">高耐磨橡胶配方与仿生齿纹设计，湿地止滑性能提升 35%，碎石硬地从容应对。</p>
                        </div>
                        <div class="col-lg-4 text-center pt16 pb16">
                            <p class="display-5 fw-bolder text-primary mb-2">CLOUDFOAM</p>
                            <h4 class="h5-fs fw-bold">云弹缓震中底</h4>
                            <p class="text-muted">超临界发泡工艺，能量回弹率高达 78%，长距离行进依然步履轻盈。</p>
                        </div>
                    </div>
                </div>
            </section>
            <section class="s_numbers pt80 pb80 text-white" style="background-color: #22332a;" data-name="品牌数字" data-snippet="s_numbers">
                <div class="container">
                    <div class="row s_nb_column_fixed align-items-center">
                        <div class="col-lg-5 pt16 pb16">
                            <h2 class="mb-3 h4-fs">源自中国鞋都 · 25 年制鞋积淀</h2>
                            <p class="lead mb-0">奥登科户外隶属晋江市奥登科鞋业有限公司，从外贸代工到自主品牌，每一步都算数。</p>
                        </div>
                        <div class="col-lg-2 offset-lg-1 text-center pt16 pb16">
                            <p class="mb-0"><span class="s_number display-1-fs">25</span><br/><span class="h5-fs">年制鞋经验</span></p>
                        </div>
                        <div class="col-lg-2 text-center pt16 pb16">
                            <p class="mb-0"><span class="s_number display-1-fs">120万+</span><br/><span class="h5-fs">双年产能</span></p>
                        </div>
                        <div class="col-lg-2 text-center pt16 pb16">
                            <p class="mb-0"><span class="s_number display-1-fs">30+</span><br/><span class="h5-fs">出口国家</span></p>
                        </div>
                    </div>
                </div>
            </section>
            <section class="s_text_image pt80 pb80" id="brand" data-name="品牌故事" data-snippet="s_text_image">
                <div class="container">
                    <div class="row align-items-center">
                        <div class="col-lg-5 pt16 pb16">
                            <h2 class="fw-bold">关于奥登科</h2>
                            <p>晋江，中国鞋都。奥登科在这里深耕制鞋 25 年，曾为多个国际户外品牌提供研发与制造服务，深谙一双好鞋的每个细节。</p>
                            <p>我们推出自主品牌「奥登科户外」，将外贸级品控标准带给每一位山友 —— 从楦型设计、材料甄选到成鞋测试，全流程自有工厂完成。</p>
                            <p>我们相信：山野之履，始于足下。</p>
                            <p><a href="/contactus" class="btn btn-secondary">联系我们</a></p>
                        </div>
                        <div class="col-lg-6 offset-lg-1 pt16 pb16">
                            <img src="/web/image/{brand_id}" class="img img-fluid mx-auto rounded shadow-sm" alt="奥登科工厂与工艺" loading="lazy"/>
                        </div>
                    </div>
                </div>
            </section>
            <section class="s_call_to_action pt48 pb48 text-white" style="background-color: #e67e22;" data-name="行动召唤" data-snippet="s_call_to_action">
                <div class="container">
                    <div class="row align-items-center">
                        <div class="col-lg-8 pt16 pb16">
                            <h3 class="mb-1 fw-bold">每一次出发，都值得一双好鞋</h3>
                            <p class="mb-0">现在下单，全场满 {free_ship} 顺丰包邮，30 天无理由退换。</p>
                        </div>
                        <div class="col-lg-4 text-lg-end pt16 pb16">
                            <a href="/shop" class="btn btn-lg btn-light text-dark fw-bold">立即选购</a>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </t>
</t>'''

arch = ARCH.format(hero_id=hero_id, brand_id=brand_id, cat_cards=cat_cards,
                   featured_cards=featured_cards, free_ship=price_str(499))

# ---------- 4. 写入首页 view ----------
page = rpc('website.page', 'search_read', [[['url', '=', '/']]],
           {'fields': ['name', 'view_id', 'website_published']})
print('首页 page:', page)
view_id = page[0]['view_id'][0] if page and page[0]['view_id'] else None
if not view_id:
    v = rpc('ir.ui.view', 'search', [[['key', '=', 'website.homepage']]])
    view_id = v[0]
rpc('ir.ui.view', 'write', [[view_id], {'arch_db': arch}])
print('首页 view(%s) 已重写 ✓' % view_id)

# SEO meta
rpc('website.page', 'write', [[page[0]['id']], {
    'website_meta_title': '奥登科户外 AUDENKO OUTDOOR — 山野之履，始于足下',
    'website_meta_description': '源自中国鞋都晋江的户外鞋品牌，25年制鞋工艺，徒步鞋、越野跑鞋、登山靴、溯溪鞋全系列装备。',
}])
print('首页 SEO 已设置 ✓')

# ---------- 5. 菜单清理与重建 ----------
menus = rpc('website.menu', 'search_read', [[['website_id', '=', 1]]],
            {'fields': ['name', 'url', 'parent_id', 'sequence', 'is_visible'], 'order': 'sequence,id'})
print('\n=== 当前菜单 ===')
for m in menus:
    print(m['id'], '|', m['name'], '|', m['url'], '| parent:', m['parent_id'], '| seq:', m['sequence'])

root_id = None
for m in menus:
    if not m['parent_id']:
        root_id = m['id']
        break
print('root menu:', root_id)

# 删除杂乱菜单：重复 Home（保留最小 id）、服务、Jobs、重复 Shop（保留最小 id）
to_delete = []
home_ids = [m['id'] for m in menus if m['name'] == 'Home']
shop_ids = [m['id'] for m in menus if m['name'] == 'Shop']
if len(home_ids) > 1:
    to_delete += home_ids[1:]
if len(shop_ids) > 1:
    to_delete += shop_ids[1:]
to_delete += [m['id'] for m in menus if m['name'] in ('服务', 'Jobs')]
to_delete = list(dict.fromkeys(to_delete))
print('删除菜单:', to_delete)
if to_delete:
    rpc('website.menu', 'unlink', [to_delete])

# 确保 Home → 首页，Shop → 全部商品
for m in menus:
    if m['id'] in to_delete:
        continue
    if m['name'] == 'Home':
        rpc('website.menu', 'write', [[m['id']], {'name': '首页', 'url': '/', 'sequence': 10, 'parent_id': root_id, 'is_visible': True}])
    if m['name'] == 'Shop':
        rpc('website.menu', 'write', [[m['id']], {'name': '全部商品', 'url': '/shop', 'sequence': 20, 'parent_id': root_id, 'is_visible': True}])

# 新增品类菜单 + 联系我们
new_menus = [
    ('徒步系列', '/shop?category=%d' % CAT_IDS['徒步系列'], 30),
    ('越野跑系列', '/shop?category=%d' % CAT_IDS['越野跑系列'], 40),
    ('登山系列', '/shop?category=%d' % CAT_IDS['登山系列'], 50),
    ('溯溪系列', '/shop?category=%d' % CAT_IDS['溯溪系列'], 60),
    ('休闲户外', '/shop?category=%d' % CAT_IDS['休闲户外'], 70),
    ('联系我们', '/contactus', 90),
]
for name, url, seq in new_menus:
    exist = rpc('website.menu', 'search', [[('name', '=', name), ('website_id', '=', 1)]])
    if not exist:
        rpc('website.menu', 'create', [{
            'name': name, 'url': url, 'sequence': seq,
            'parent_id': root_id, 'website_id': 1, 'is_visible': True}])
print('菜单已重建 ✓')

# ---------- 6. 品牌CSS：上传文件 + 注册资产 ----------
from bt_exec import BTExec
ex = BTExec()
b64 = base64.b64encode(open(CSS_LOCAL, 'rb').read()).decode()
chunks = [b64[i:i + 30000] for i in range(0, len(b64), 30000)]
ex.run('rm -f /tmp/adk.b64', timeout=15, name='adk-css')
for c in chunks:
    ex.run("echo -n %s >> /tmp/adk.b64" % c, timeout=15, name='adk-css')
out = ex.run('base64 -d /tmp/adk.b64 > %s && chown odoo20:odoo20 %s && rm -f /tmp/adk.b64 && echo CSS_OK' % (CSS_REMOTE, CSS_REMOTE),
             timeout=30, name='adk-css')
print('CSS 上传:', 'OK' if 'CSS_OK' in out else out[-200:])

exist_asset = rpc('ir.asset', 'search', [[('path', '=', 'theme_liquid_glass/static/src/css/adk_outdoor.css')]])
if not exist_asset:
    rpc('ir.asset', 'create', [{
        'name': 'adk_outdoor.css', 'bundle': 'web.assets_frontend',
        'directive': 'append', 'path': 'theme_liquid_glass/static/src/css/adk_outdoor.css',
        'website_id': 1, 'active': True}])
    print('ir.asset 已注册 ✓')
else:
    print('ir.asset 已存在 ✓')

print('\n=== setup_homepage 完成 ===')
