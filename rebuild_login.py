#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""登录页品牌化重构：分屏布局（左品牌大图 / 右登录表单）"""
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
print('登录 ✓')


def create_view(key, base_key, arch, active=True):
    exist = rpc('ir.ui.view', 'search', [[['key', '=', key]]])
    if exist:
        rpc('ir.ui.view', 'write', [exist, {'arch_db': arch, 'active': active}])
        print('%s 已更新 ✓' % key)
        return exist[0]
    base = rpc('ir.ui.view', 'search', [[['key', '=', base_key]]])
    if not base:
        raise SystemExit('base 视图不存在: %s' % base_key)
    vid = rpc('ir.ui.view', 'create', [{
        'name': key, 'key': key, 'type': 'qweb',
        'inherit_id': base[0], 'arch_db': arch, 'active': active}])
    print('%s 已创建 ✓ (id=%s)' % (key, vid))
    return vid


# ============ 1. 分屏布局：左品牌面板（website.login_layout） ============
LOGIN_LEFT = '''<data>
    <xpath expr="//div[hasclass('oe_website_login_container')]" position="attributes">
        <attribute name="class">oe_website_login_container adk-login-right</attribute>
    </xpath>
    <xpath expr="//div[hasclass('oe_website_login_container')]" position="before">
        <div class="adk-login-left d-none d-lg-flex flex-column justify-content-between text-white oe_unremovable">
            <div class="adk-login-left-brand d-flex align-items-center gap-2 pt-4 ps-4">
                <img src="/web/image/website/1/logo" alt="奥登科户外" style="height: 34px;"/>
                <span class="fw-bold" style="letter-spacing: .12em;">AUDENKO OUTDOOR</span>
            </div>
            <div class="adk-login-left-hero px-5 pb-2">
                <h2 class="display-4 fw-bolder mb-3">山野之履<br/>始于足下</h2>
                <p class="lead mb-4" style="max-width: 26rem;">奥登科户外全渠道管理平台 —— 从产品、订单到客户，一站式驾驭您的户外装备生意。</p>
                <ul class="list-unstyled d-flex flex-column gap-3 mb-0 adk-login-points">
                    <li class="d-flex align-items-center gap-2">
                        <i class="oi oi-filled rounded-circle bg-primary d-inline-flex justify-content-center align-items-center" data-icon="check" role="img" style="width:22px;height:22px;font-size:12px;"/>
                        <span>25 年制鞋积淀 · 晋江自有工厂</span>
                    </li>
                    <li class="d-flex align-items-center gap-2">
                        <i class="oi oi-filled rounded-circle bg-primary d-inline-flex justify-content-center align-items-center" data-icon="check" role="img" style="width:22px;height:22px;font-size:12px;"/>
                        <span>5 大系列 · 12 款产品全渠道同步</span>
                    </li>
                    <li class="d-flex align-items-center gap-2">
                        <i class="oi oi-filled rounded-circle bg-primary d-inline-flex justify-content-center align-items-center" data-icon="check" role="img" style="width:22px;height:22px;font-size:12px;"/>
                        <span>订单 · 库存 · 客户数据实时掌握</span>
                    </li>
                </ul>
            </div>
            <div class="px-4 pb-3 small adk-login-left-copy">© 2026 晋江市奥登科鞋业有限公司 · 奥登科户外</div>
        </div>
    </xpath>
</data>'''
create_view('adk_outdoor.login_brand_panel', 'website.login_layout', LOGIN_LEFT)

# ============ 2. 表单区优化（web.login） ============
LOGIN_FORM = '''<data>
    <xpath expr="//form[@data-captcha='login']" position="before">
        <div class="adk-login-head text-center mb-4">
            <img t-if="not res_company.uses_default_logo" src="/web/image/website/1/logo" alt="奥登科户外" class="adk-login-logo mb-3"/>
            <h2 class="h3-fs fw-bold mb-1">欢迎回来</h2>
            <p class="text-muted small mb-0">登录奥登科户外管理平台，继续您的旅程</p>
        </div>
    </xpath>
    <xpath expr="//div[@id='oe_structure_login_bottom']" position="before">
        <div class="text-center small mt-3 adk-login-back">
            <a href="/" class="text-decoration-none">
                <i class="oi me-1" data-icon="arrow_back" role="img"/>返回官网
            </a>
        </div>
    </xpath>
</data>'''
create_view('adk_outdoor.login_form_zh', 'web.login', LOGIN_FORM)

print('\n=== 视图创建完成 ===')
