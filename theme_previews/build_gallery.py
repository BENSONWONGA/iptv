#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成自包含的 Odoo 免费主题预览画廊 HTML（图片 base64 内嵌，单文件可分享）"""
import base64
import io
import os

try:
    from PIL import Image
except ImportError:
    Image = None

D = '/workspace/theme_previews'
OUT = os.path.join(D, 'odoo_free_themes.html')
MAXW = 1280


def to_data_uri(fname):
    p = os.path.join(D, fname)
    if not os.path.exists(p):
        return None
    if fname.endswith('.gif'):
        with open(p, 'rb') as f:
            return 'data:image/gif;base64,' + base64.b64encode(f.read()).decode()
    if Image is None:
        mime = 'image/png' if fname.endswith('.png') else 'image/jpeg'
        with open(p, 'rb') as f:
            return 'data:%s;base64,' % mime + base64.b64encode(f.read()).decode()
    im = Image.open(p)
    if im.mode != 'RGB':
        im = im.convert('RGBA')
        bg = Image.new('RGB', im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert('RGB')
    w, h = im.size
    if w > MAXW:
        rs = getattr(Image, 'LANCZOS', None)
        im = im.resize((MAXW, int(h * MAXW / w)), rs)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=82, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()


THEMES = [
    {
        'cat': '后端主题（Backend · Odoo 20 社区版）',
        'name': 'MuK Backend Theme',
        'tech': 'muk_web_theme',
        'vendor': 'MuK IT',
        'stats': '87,932 下载 · 87 条评价 · 老牌经典',
        'desc': 'Odoo 社区版下载量第一的免费后端主题。深蓝灰深色应用中心 + 白色圆角应用卡片，'
                '重塑应用、设置、Chatter、移动端整套后台体验，桌面/移动端自适应。',
        'tags': ['深色应用中心', '设置页美化', 'Chatter 侧栏', '移动端适配'],
        'images': [
            ('muk_screenshot_apps.png', '应用中心：深色底 + 白色圆角卡片 + 彩色图标'),
            ('muk_screenshot_backend.png', '后端视图'),
            ('muk_screenshot_settings.png', '设置页'),
            ('muk_screenshot_chatter.png', 'Chatter 侧栏'),
        ],
        'url': 'https://apps.odoo.com/apps/themes/20.0/muk_web_theme',
    },
    {
        'cat': '后端主题（Backend · Odoo 20 社区版）',
        'name': 'Code Backend Theme',
        'tech': 'code_backend_theme',
        'vendor': 'Cybrosys Techno Solutions',
        'stats': '29,046 下载 · 25 条评价',
        'desc': 'Cybrosys 出品的浅色系后端主题：白底 + Odoo 品牌紫主按钮，整体干净、接近官方风格但更精致，'
                '应用中心、讨论、员工等视图统一美化。适合喜欢浅色后台的你。',
        'tags': ['浅色白底', '品牌紫', '整套视图美化'],
        'images': [
            ('code_apps.png', '应用中心：浅色 + 紫色主按钮'),
            ('code_discuss.png', '讨论应用'),
            ('code_employees.png', '员工应用'),
        ],
        'url': 'https://apps.odoo.com/apps/themes/20.0/code_backend_theme',
    },
    {
        'cat': '后端主题（Backend · Odoo 20 社区版）',
        'name': 'DevsCodespace Backend Theme',
        'tech': 'dcs_backend_theme',
        'vendor': 'Ankit',
        'stats': '新上架 · 26 下载 · 功能最全',
        'desc': 'Odoo 20 新锐主题，配置项最丰富：4 种导航模式（侧边栏 / 顶栏 / 紧凑 / 应用抽屉）一键切换，'
                '深色模式、全局搜索、书签、色板、分屏视图、Chatter 位置、登录页布局全部可配。',
        'tags': ['4 种导航模式', '深色模式', '全局搜索', '登录页定制'],
        'images': [
            ('dcs_nav_modes.jpg', '四种导航模式：Sidebar / Top bar / Compact / App drawer'),
            ('dcs_dark_mode.jpg', '深色模式'),
            ('dcs_global_search.jpg', '全局搜索'),
            ('dcs_login_layouts.jpg', '登录页布局（多种可选）'),
        ],
        'url': 'https://apps.odoo.com/apps/themes/20.0/dcs_backend_theme',
    },
    {
        'cat': '后端主题（Backend · Odoo 20 社区版）',
        'name': 'Clarity Backend Theme',
        'tech': 'clarity_backend_theme_bits',
        'vendor': 'Terabits Technolab',
        'stats': '5,339 下载 · 8 条评价',
        'desc': '深色侧边栏 + 浅色工作区的混搭风格（类 Slack / Teams 布局），带应用抽屉、深色模式、'
                '多标签支持、登录页重构，列表与看板视图增强。',
        'tags': ['深色侧边栏', '应用抽屉', '多标签', '登录页重构'],
        'images': [
            ('clarity_1.png', '讨论应用：深色侧栏 + 浅色三栏工作区'),
            ('clarity_2.png', '界面细节 2'),
            ('clarity_3.png', '界面细节 3'),
        ],
        'url': 'https://apps.odoo.com/apps/themes/20.0/clarity_backend_theme_bits',
    },
    {
        'cat': '后端主题（Backend · Odoo 20 社区版）',
        'name': 'Chameleon Multi Color Backend Theme',
        'tech': 'multicolor_backend_theme',
        'vendor': 'Cybrosys Techno Solutions',
        'stats': '3,758 下载 · 39 条评价',
        'desc': '主打「任意主色可配置」：顶部栏、侧边栏、表单、看板全部跟随主题色切换（演示为草绿色），'
                '适合想给后台套品牌色的团队。',
        'tags': ['多色可配置', '表单/看板增强', '品牌色跟随'],
        'images': [
            ('cham_sidebar.png', '销售列表：草绿顶栏 + 深色侧栏'),
            ('cham_form.png', '表单视图'),
            ('cham_kanban.png', '看板视图'),
        ],
        'url': 'https://apps.odoo.com/apps/themes/20.0/multicolor_backend_theme',
    },
    {
        'cat': '后端主题（Backend · Odoo 20 社区版）',
        'name': 'Web Responsive Enterprise',
        'tech': 'web_responsive_enterprise',
        'vendor': 'Arun A George',
        'stats': '163 下载 · 47 条评价',
        'desc': '一句话：社区版秒变企业版外观。浅色模式，企业版风格的应用抽屉、表单、看板、列表，'
                '不需要企业版授权也有企业版的「脸」。',
        'tags': ['企业版外观', '浅色模式', '应用抽屉'],
        'images': [
            ('wre_screenshot_app_drawer.png', '应用抽屉（企业版风格）'),
            ('wre_screenshot_form.png', '表单视图'),
            ('wre_screenshot_kanban.png', '看板视图'),
        ],
        'url': 'https://apps.odoo.com/apps/themes/20.0/web_responsive_enterprise',
    },
    {
        'cat': '网站 / 电商主题（Website · Odoo 20）',
        'name': 'Theme Boec',
        'tech': 'theme_boec',
        'vendor': 'Cybrosys Techno Solutions',
        'stats': '8,279 下载 · 62 条评价 · 免费电商第一',
        'desc': 'Odoo 20 免费电商主题里最热门的一款：蓝白极简时尚风，大图 Hero + 促销横幅 + 商品网格 + 博客模块，'
                '购物车、联系页、商品列表全套电商页面。这种「时尚单品」气质和户外鞋服品牌契合度很高。',
        'tags': ['时尚电商', '蓝白极简', '全套电商页', '移动端'],
        'images': [
            ('boec_hero.png', '首页/购物车/商品列表/博客 多屏展示'),
            ('boec_laptop.jpg', '桌面端整站'),
            ('boec_phone.jpg', '移动端整站'),
            ('boec_2.jpg', '版面细节'),
            ('boec_5.jpg', '版面细节'),
        ],
        'url': 'https://apps.odoo.com/apps/themes/20.0/theme_boec',
    },
    {
        'cat': '网站 / 电商主题（Website · Odoo 20）',
        'name': 'Theme WatchHut',
        'tech': 'theme_watchhut',
        'vendor': 'Cybrosys Techno Solutions',
        'stats': '1,115 下载 · 8 条评价',
        'desc': '高端精品店铺风格：白底黑字 + 衬线大标题 + 杂志式瀑布流商品网格，「数字展厅」质感，'
                '适合走高调性、重品牌路线的品类。',
        'tags': ['极简精品', '杂志式排版', '品牌调性'],
        'images': [
            ('watch_1.jpg', '首页：桌面端 + 移动端'),
            ('watch_laptop.jpg', '整站预览'),
            ('watch_shop.png', '商店页'),
        ],
        'url': 'https://apps.odoo.com/apps/themes/20.0/theme_watchhut',
    },
    {
        'cat': '网站 / 电商主题（Website · Odoo 20）',
        'name': 'Theme Crest',
        'tech': 'theme_crest',
        'vendor': 'Terabits Technolab',
        'stats': '576 下载 · 45 条评价',
        'desc': '前端 + 后端一体的主题：网站侧有高级页头页脚、响应式电商页面、增强版商品卡片（可展示附加属性），'
                '后端侧也有配套优化。下面是官方动态演示（GIF）。',
        'tags': ['前后端一体', '商品卡片增强', '页头页脚'],
        'images': [
            ('crest_intro.gif', '官方动态演示'),
        ],
        'url': 'https://apps.odoo.com/apps/themes/20.0/theme_crest',
    },
]

CSS = """
:root { --accent:#06bea0; --ink:#22303f; --sub:#6b7a8c; --line:#e5e9ee; --bg:#f4f6f8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
       font-family:-apple-system,"PingFang SC","Microsoft YaHei","Segoe UI",Roboto,sans-serif; }
.wrap { max-width:1080px; margin:0 auto; padding:36px 20px 60px; }
h1 { font-size:25px; margin:0 0 6px; }
.sub { color:var(--sub); font-size:13.5px; margin-bottom:8px; }
.cat { margin:36px 0 14px; font-size:17px; display:flex; align-items:center; gap:10px; }
.cat .n { background:var(--accent); color:#fff; font-size:12px; border-radius:20px; padding:2px 10px; }
.card { background:#fff; border:1px solid var(--line); border-radius:14px; padding:22px; margin-bottom:22px;
        box-shadow:0 1px 3px rgba(20,40,60,.05); }
.card h2 { margin:0; font-size:19px; display:inline; }
.card .tech { font-weight:400; font-size:13px; color:var(--sub); margin-left:8px; }
.meta { color:var(--sub); font-size:13px; margin:8px 0 10px; }
.meta b { color:#0a8f7a; }
.tags { margin:2px 0 8px; }
.tag { display:inline-block; background:#eef7f5; color:#0a8f7a; border-radius:6px; padding:2px 9px;
       font-size:12px; margin:0 6px 6px 0; }
.desc { font-size:14px; line-height:1.75; color:#3a4757; }
.shots { margin-top:14px; display:grid; gap:12px; }
.shots figure { margin:0; }
.shots img { width:100%; height:auto; border:1px solid var(--line); border-radius:10px; display:block; background:#fff; }
.shots figcaption { font-size:12px; color:var(--sub); margin-top:5px; }
.store { display:inline-block; margin-top:12px; color:var(--accent); font-size:13px; text-decoration:none; font-weight:600; }
.note { background:#fff; border:1px dashed #cfd8e0; border-radius:14px; padding:18px 22px;
        font-size:13.5px; line-height:1.95; color:#3a4757; margin-top:34px; }
.note b { color:var(--ink); }
"""

parts = []
parts.append('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
             '<meta name="viewport" content="width=device-width, initial-scale=1">'
             '<title>免费 Odoo 20 主题预览</title><style>%s</style></head><body><div class="wrap">' % CSS)
parts.append('<h1>免费 Odoo 主题预览 <span style="font-size:14px;color:var(--sub);font-weight:400">'
             'Odoo 20 · 社区版适配</span></h1>')
parts.append('<div class="sub">数据与截图来自 Odoo 应用商店 apps.odoo.com（2026-10）· 共 9 款：后端 6 款 + 网站/电商 3 款</div>')

cur_cat = None
n_img = 0
for t in THEMES:
    if t['cat'] != cur_cat:
        cur_cat = t['cat']
        cnt = sum(1 for x in THEMES if x['cat'] == cur_cat)
        parts.append('<div class="cat"><span class="n">%d 款</span>%s</div>' % (cnt, cur_cat))
    parts.append('<div class="card">')
    parts.append('<h2>%s</h2><span class="tech">模块名：%s · %s</span>' % (t['name'], t['tech'], t['vendor']))
    parts.append('<div class="meta"><b>%s</b></div>' % t['stats'])
    parts.append('<div class="tags">%s</div>' % ''.join('<span class="tag">%s</span>' % x for x in t['tags']))
    parts.append('<div class="desc">%s</div>' % t['desc'])
    parts.append('<div class="shots">')
    for fname, cap in t['images']:
        uri = to_data_uri(fname)
        if uri:
            n_img += 1
            parts.append('<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>' % (uri, cap, cap))
        else:
            parts.append('<figure><figcaption>缺图：%s</figcaption></figure>' % fname)
    parts.append('</div>')
    parts.append('<a class="store" href="%s" target="_blank">应用商店页面 →</a>' % t['url'])
    parts.append('</div>')

parts.append('<div class="note">'
             '<b>几点说明：</b><br>'
             '1. 你现在装的 <b>Liquid Glass</b> 就是免费榜第 2 名（Cybrosys，3,524 下载），不用重复安装。<br>'
             '2. 免费网站主题大多只更新到 Odoo 19（Autofly、Velora、Eco Food、Xtream 等），'
             '<b>Odoo 20 能装的免费电商主题目前就是 Boec / WatchHut / Crest 这三款</b>。<br>'
             '3. 其他 20.0 免费后端主题还有：3A-dealer（藏青+金侧栏）、FlousFlow（响应式+深色）、'
             'Home Screen Designer、Badirra Enterprise Community 等，需要的话我再补预览。<br>'
             '4. 电商主题会整体替换网站外观——你现在的奥登科首页是定制搭的，<b>安装前我会先做完整备份</b>，'
             '不满意可一键回退。<br>'
             '5. 看中哪款直接告诉我名字，我下载部署到服务器安装调试。'
             '</div>')
parts.append('</div></body></html>')

html = '\n'.join(parts)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
print('生成完成: %s' % OUT)
print('内嵌图片: %d 张' % n_img)
print('文件大小: %.1f MB' % (os.path.getsize(OUT) / 1048576))
