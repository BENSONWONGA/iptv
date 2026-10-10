# -*- coding: utf-8 -*-
"""指令部件条码 PDA 扫码作业页：/odk/dispatch/scan（需登录）"""
from odoo import http
from odoo.http import request


class OdkDispatchScanController(http.Controller):
    @http.route("/odk/dispatch/scan", type="http", auth="user", website=False)
    def scan_parts_page(self, **kw):
        return request.render("odk_dispatch.scan_parts_page")
