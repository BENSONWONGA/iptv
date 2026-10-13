#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Odoo 20 免费网站模板预览画廊 v2（官方12款实时截图 + 第三方3款）"""
import base64
import io
import os

from PIL import Image

D = '/workspace/theme_previews'
OUT = os.path.join(D, 'odoo_website_themes.html')
MAXW = 1150


def to_data_uri(fname, maxw=MAXW, quality=74):
    p = os.path.join(D, fname)
    if not os.path.exists(p):
        return None
    im = Image.open(p)
    if im.mode != 'RGB':
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    w, h = im.size
    if w > maxw:
        rs = getattr(Image, 'LANCZOS', None)
        im = im.resize((maxw, int(h * maxw / w)), rs)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=quality, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


HOST = 'http://220.162.99.166:9000'

OFFICIAL = [
    ('theme_anelusia', 'Anelusia', '时尚 · 鞋服 · 运动 · 健身', '2,287 下载',
     '官方定位就是「Clothes, Shoes, Sports, Fitness」——和奥登科户外鞋品类契合度最高的一款。多彩活泼、大图视觉、青春潮流感。',
     '与户外品牌最搭'),
    ('theme_kea', 'Kea', '电子 · 数码商城', '3,056 下载',
     '官方描述：深色发光 hero + 购物属性横排 + 柔和卡片 + 滚动公告 + bento 网格。现代电商风，暗色高级感。',
     '暗色现代电商'),
    ('theme_loftspace', 'Loftspace', '家具 · 玩具 · 零售', '9,186 下载（官方第一）',
     '官方免费主题下载量冠军。 Loft 工业风 + 大气留白，适合追求品质感的零售店。',
     '官方下载第一'),
    ('theme_treehouse', 'Treehouse', '自然 · 户外 · 绿色', '3,434 下载',
     '自然木质感 + 森林绿基调，户外/自然/环保类品牌的官方首选模板。',
     '自然户外风'),
    ('theme_enark', 'Enark', '企业 · 服务', '4,882 下载',
     '干净的企业服务型模板，排版规整、专业稳重，适合品牌站+内容站。',
     '企业服务风'),
    ('theme_graphene', 'Graphene', '科技 · 机器人 · IT 服务', '5,512 下载',
     '科技感十足：几何图形、深浅对比、动效丰富，科技类品牌的高人气选择。',
     '科技感强'),
    ('theme_bistro', 'Bistro', '餐厅 · 咖啡 · 餐饮', '3,001 下载',
     '餐饮行业官方模板：暖色调、菜品大图、菜单排版，也可借其「生活方式」气质做品牌站。',
     '餐饮生活方式'),
    ('theme_cobalt', 'Cobalt', 'IT · 开发 · 技术博客', '2,388 下载',
     '极简技术风：代码感排版、单色强调，适合开发者/技术品牌。',
     '极简技术风'),
    ('theme_beauty', 'Beauty', '美妆 · 健康 · 个护', '1,742 下载',
     '柔和渐变 + 优雅衬线，美妆个护类官方模板，视觉精致。',
     '柔和精致'),
    ('theme_orchid', 'Orchid', '花艺 · 园艺 · 自然', '1,440 下载',
     '花艺绿植类官方模板，清新自然，图片驱动的排版。',
     '清新自然'),
    ('theme_nano', 'Nano', '设计 · 极简', '1,531 下载',
     '极简主义设计模板：大留白、大字排版、少即是多。',
     '极简大字版式'),
    ('theme_avantgarde', 'Avantgarde', '先锋 · 创意', '1,233 下载',
     '先锋设计感：不对称布局、大胆用色，想要「与众不同」就选它。',
     '先锋创意'),
]

THIRD = [
    ('Theme Boec', 'theme_boec', 'Cybrosys', '8,279 下载 · 62 评价', '免费电商第一',
     '蓝白极简时尚风：大图 Hero + 促销横幅 + 商品网格 + 博客，购物车/联系页/商品列表全套电商页。第三方免费电商里最热门。',
     ['boec_hero.png', 'boec_laptop.jpg', 'boec_phone.jpg', 'boec_5.jpg'],
     ['首页多屏展示', '桌面端整站', '移动端整站', '版面细节']),
    ('Theme WatchHut', 'theme_watchhut', 'Cybrosys', '1,115 下载 · 8 评价', '精品店铺风',
     '白底黑字 + 衬线大标题 + 杂志式瀑布流，「数字展厅」质感，走高调性品牌路线。',
     ['watch_1.jpg', 'watch_laptop.jpg', 'watch_shop.png'],
     ['首页：桌面+移动', '整站预览', '商店页']),
    ('Theme Crest', 'theme_crest', 'Terabits', '576 下载 · 45 评价', '前后端一体',
     '前端高级页头页脚 + 响应式电商页 + 增强版商品卡片；后端也有配套优化（动态演示 GIF）。',
     ['crest_intro.gif'],
     ['官方动态演示']),
]

CSS = """
:root { --accent:#06bea0; --ink:#22303f; --sub:#6b7a8c; --line:#e5e9ee; --bg:#f4f6f8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font-family:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI",Roboto,sans-serif; }
.wrap { max-width:1120px; margin:0 auto; padding:36px 20px 60px; }
h1 { font-size:25px; margin:0 0 6px; }
.sub { color:var(--sub); font-size:13.5px; margin-bottom:6px; }
.cat { margin:38px 0 16px; font-size:17px; display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.cat .n { background:var(--accent); color:#fff; font-size:12px; border-radius:20px; padding:2px 10px; }
.card { background:#fff; border:1px solid var(--line); border-radius:14px; padding:22px; margin-bottom:22px;
        box-shadow:0 1px 3px rgba(20,40,60,.05); }
.card h2 { margin:0; font-size:19px; display:inline; }
.card .tech { font-weight:400; font-size:13px; color:var(--sub); margin-left:8px; }
.meta { color:var(--sub); font-size:13px; margin:8px 0 8px; }
.meta b { color:#0a8f7a; }
.badge { display:inline-block; background:#eef7f5; color:#0a8f7a; border-radius:6px; padding:2px 9px;
         font-size:12px; margin-left:8px; vertical-align:2px; }
.desc { font-size:14px; line-height:1.75; color:#3a4757; }
.shot { margin-top:14px; }
.shot img { width:100%; height:auto; border:1px solid var(--line); border-radius:10px; display:block; }
.cap { font-size:12px; color:var(--sub); margin-top:5px; }
.links { margin-top:12px; }
.links a { display:inline-block; margin-right:16px; color:var(--accent); font-size:13px;
           text-decoration:none; font-weight:600; }
.note { background:#fff; border:1px dashed #cfd8e0; border-radius:14px; padding:18px 22px;
        font-size:13.5px; line-height:1.95; color:#3a4757; margin-top:34px; }
.note b { color:var(--ink); }
.toc { background:#fff; border:1px solid var(--line); border-radius:14px; padding:16px 22px;
       font-size:13px; line-height:2; margin-top:20px; }
.toc a { color:#3a4757; text-decoration:none; margin-right:14px; white-space:nowrap; }
.toc a:hover { color:var(--accent); }
"""

parts = []
parts.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width, initial-scale=1">'
             '<title>免费 Odoo 20 网站模板预览</title><style>%s</style></head><body><div class="wrap">' % CSS)
parts.append('<h1>免费 Odoo 网站模板预览 <span style="font-size:14px;color:var(--sub);font-weight:400">'
             'Odoo 20 · 15 款：官方 12 + 第三方 3</span></h1>')
parts.append('<div class="sub">官方 12 款的截图来自你服务器上实时渲染的官方预览页（非商店缩略图）· 2026-10</div>')

toc = ['<div class="toc"><b>快速跳转：</b>']
for t in OFFICIAL:
    toc.append('<a href="#%s">%s</a>' % (t[0], t[1]))
for t in THIRD:
    toc.append('<a href="#%s">%s</a>' % (t[1], t[0]))
toc.append('</div>')
parts.append(''.join(toc))

parts.append('<div class="cat"><span class="n">12 款</span>Odoo 官方免费模板 '
             '<span style="font-size:12px;color:var(--sub);font-weight:400">Odoo S.A. 出品 · 全部适配 20.0 · 点击链接可看在线全尺寸预览</span></div>')
for tech, name, cat, dl, desc, badge in OFFICIAL:
    uri = to_data_uri('preview_%s.png' % tech)
    parts.append('<div class="card" id="%s">' % tech)
    parts.append('<h2>%s</h2><span class="tech">%s · %s</span><span class="badge">%s</span>' % (name, tech, cat, badge))
    parts.append('<div class="meta"><b>%s</b> · Odoo S.A. 官方 · 免费 LGPL</div>' % dl)
    parts.append('<div class="desc">%s</div>' % desc)
    if uri:
        parts.append('<div class="shot"><img src="%s" alt="%s"><div class="cap">%s 官方预览页（完整长图，点击下方链接看交互版）</div></div>'
                     % (uri, name, name))
    parts.append('<div class="links"><a href="%s/%s/static/description/preview.html" target="_blank">在线交互预览 →</a>'
                 '<a href="https://apps.odoo.com/apps/themes/20.0/%s" target="_blank">应用商店页面 →</a></div>'
                 % (HOST, tech, tech))
    parts.append('</div>')

parts.append('<div class="cat"><span class="n">3 款</span>第三方免费电商模板 '
             '<span style="font-size:12px;color:var(--sub);font-weight:400">Odoo 20 可装的免费电商主题就这三款</span></div>')
for name, tech, vendor, dl, badge, desc, imgs, caps in THIRD:
    parts.append('<div class="card" id="%s">' % tech)
    parts.append('<h2>%s</h2><span class="tech">%s · %s</span><span class="badge">%s</span>' % (name, tech, vendor, badge))
    parts.append('<div class="meta"><b>%s</b> · 免费 LGPL</div>' % dl)
    parts.append('<div class="desc">%s</div>' % desc)
    for i, fn in enumerate(imgs):
        uri = to_data_uri(fn)
        if uri:
            parts.append('<div class="shot"><img src="%s" alt="%s"><div class="cap">%s</div></div>'
                         % (uri, name, caps[i] if i < len(caps) else ''))
    parts.append('<div class="links"><a href="https://apps.odoo.com/apps/themes/20.0/%s" target="_blank">应用商店页面 →</a></div>' % tech)
    parts.append('</div>')

parts.append('<div class="note">'
             '<b>说明：</b><br>'
             '1. <b>官方 12 款已在你服务器上就绪</b>（源码已部署，不需要登录商店下载）。看中哪款告诉我名字即可安装。<br>'
             '2. 官方主题的「在线交互预览」链接是静态预览页，直接在你服务器上打开，可缩放浏览。<br>'
             '3. 想真实体验某款主题装在网站上的效果：我建了演示库 <b>theme_demo</b>（当前装着 Anelusia），'
             '访问 <a href="%s/?db=theme_demo" style="color:var(--accent)">%s/?db=theme_demo</a>，'
             '登录 admin / Demo@2026 可进后台看。要换哪款告诉我。<br>'
             '4. 第三方 3 款（Boec / WatchHut / Crest）需要从商店下载 zip（要登录 odoo.com 账号），你下载后上传给我即可装。<br>'
             '5. 你的生产站 benson 完全没动过：奥登科前台 + 浅色后台一切如常。<br>'
             '6. 给户外鞋品牌的角度：<b>Anelusia（鞋服运动）</b>、<b>Treehouse（自然户外）</b>、<b>Kea（现代电商）</b>、'
             '<b>Loftspace（品质零售）</b> 值得优先细看。'
             '</div>' % (HOST, HOST))
parts.append('</div></body></html>')

html = '\n'.join(parts)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
print('生成: %s' % OUT)
print('大小: %.1f MB' % (os.path.getsize(OUT) / 1048576))
