{
    "name": "奥登科·HTTP环境兼容垫片",
    "version": "20.0.1.0.0",
    "category": "Hidden/Tools",
    "summary": "纯HTTP(IP直连)部署下补齐浏览器安全API(clipboard)，修复Odoo20教程组件加载报错弹窗",
    "description": "浏览器只在安全上下文(HTTPS/localhost)提供 navigator.clipboard。本服务器用 http://IP:88 访问，该API缺失导致 web_tour 的 tour_helpers_clipboard 模块加载崩溃并弹出'哎呀'报错框。本模块在公共资源包最前注入垫片，补齐该API，消除报错。",
    "author": "奥登科",
    "license": "LGPL-3",
    "depends": ["web"],
    "assets": {
        "web.assets_common": [
            "odk_http_shim/static/src/js/clipboard_shim.js",
        ],
    },
    "installable": True,
}
