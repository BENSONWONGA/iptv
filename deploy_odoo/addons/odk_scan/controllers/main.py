# -*- coding: utf-8 -*-
"""扫码页路由：/odk/scan（需登录，仓库 PDA 登录一次即可常驻使用）"""
from odoo import http
from odoo.http import request


class OdkScanController(http.Controller):
    @http.route("/odk/scan", type="http", auth="user", website=False)
    def scan_page(self, **kw):
        return request.render("odk_scan.scan_page")
