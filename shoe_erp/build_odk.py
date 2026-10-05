# -*- coding: utf-8 -*-
"""构建部署产物：
1. odk.html        —— 单文件静态版（备用）
2. odk_webpage.html —— Web Page main_section_html 版（内联 CSS/JS + 隐藏 Frappe 站点导航）
"""
import os
import re

UI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")
HERE = os.path.dirname(os.path.abspath(__file__))

html = open(os.path.join(UI, "index.html"), encoding="utf-8").read()
css = open(os.path.join(UI, "app.css"), encoding="utf-8").read()
js = open(os.path.join(UI, "app.js"), encoding="utf-8").read()

assert "</script>" not in js and "</style>" not in css
assert "{{" not in js + css and "{%" not in js + css, "Jinja 误解析风险"

# ---- 产物1：单文件静态版 ----
odk = html.replace('<link rel="stylesheet" href="app.css">', "<style>\n" + css + "\n</style>")
odk = odk.replace('<script src="app.js"></script>', "<script>\n" + js + "\n</script>")
assert "<style>" in odk and 'src="app.js"' not in odk
out1 = os.path.join(HERE, "odk.html")
open(out1, "w", encoding="utf-8").write(odk)
print(f"已生成 {out1}  ({os.path.getsize(out1) / 1024:.1f} KB)")

# ---- 产物2：Web Page 版（body 内容 + 内联样式/脚本 + 容器适配） ----
# body 从原始 index.html 提取（仅有外链 script/css 引用），避免脚本重复注入
m = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
body = m.group(1)
body = body.replace('<script src="app.js"></script>', "")

# 容器适配：隐藏 Frappe 站点 navbar/footer/breadcrumbs，清除其内边距
ADAPT_CSS = """
/* ===== 部署容器适配（Web Page 场景）===== */
body { padding: 0 !important; margin: 0 !important; background: #0C1118 !important; }
nav.navbar, .navbar, .page-breadcrumbs, footer, .web-footer,
.page-header-wrapper, .standard-navbar, .standard-footer { display: none !important; }
.page-content-wrapper, .page_content, main.page-content, #page-odk { padding: 0 !important; margin: 0 !important; }
"""

webpage_content = (
    "<style>\n" + css + "\n" + ADAPT_CSS + "\n</style>\n"
    + body
    + "\n<script>\n" + js + "\n</script>"
)
out2 = os.path.join(HERE, "odk_webpage.html")
open(out2, "w", encoding="utf-8").write(webpage_content)
print(f"已生成 {out2}  ({os.path.getsize(out2) / 1024:.1f} KB)")
