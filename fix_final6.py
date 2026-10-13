#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复6：页脚品牌化 + shell翻译重载 + 重启Odoo"""
import time

import requests

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'
s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=900):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}}}, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError('%s/%s: %s' % (model, method, json.dumps(d['error'], ensure_ascii=False)[:400]))
    return d['result']


s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)

# ---------- 1. 页脚品牌化 ----------
FOOTER_ARCH = '''<data name="Default">
    <xpath expr="//div[@id='footer']" position="replace">
        <div id="footer" class="oe_structure oe_structure_solo border text-break" t-ignore="true" t-if="not no_footer" style="--box-border-left-width: 0px; --box-border-right-width: 0px;">
            <section class="s_text_block pt40 pb16" data-snippet="s_text_block" data-name="Container">
                <div class="container">
                    <div class="row">
                        <div class="col-lg-2 pt24 pb24">
                            <h5>快捷导航</h5>
                            <ul class="list-unstyled">
                                <li><a href="/">首页</a></li>
                                <li><a href="/shop">全部商品</a></li>
                                <li><a href="/shop?category=1">徒步系列</a></li>
                                <li><a href="/shop?category=2">越野跑系列</a></li>
                                <li><a href="/shop?category=3">登山系列</a></li>
                                <li><a href="/shop?category=4">溯溪系列</a></li>
                                <li><a href="/contactus">联系我们</a></li>
                            </ul>
                        </div>
                        <div class="col-lg-5 pt24 pb24">
                            <h5>关于奥登科</h5>
                            <p>奥登科户外（AUDENKO OUTDOOR）隶属晋江市奥登科鞋业有限公司，源自"中国鞋都"晋江，深耕制鞋 25 年。我们以外贸级品控标准打造徒步鞋、越野跑鞋、登山靴与溯溪鞋，让每一次出发都安心可靠。</p>
                            <p class="text-muted mb-0">山野之履，始于足下。</p>
                        </div>
                        <div class="col-lg-4 offset-lg-1 pt24 pb24">
                            <h5>联系我们</h5>
                            <ul class="list-unstyled">
                                <li><i class="oi oi-filled oi-fw me-2" data-icon="chat_bubble"/><a href="/contactus">在线留言</a></li>
                                <li><i class="oi oi-filled oi-fw me-2" data-icon="mail"/><a href="mailto:service@audenko-outdoor.com">service@audenko-outdoor.com</a></li>
                                <li><i class="oi oi-filled oi-fw me-2" data-icon="phone"/><a href="tel:+865958888666"><span class="o_force_ltr">+86 595-8888 6666</span></a></li>
                                <li class="text-muted">福建省晋江市陈埭镇鞋都路 188 号</li>
                            </ul>
                        </div>
                    </div>
                    <div class="row">
                        <div class="col-lg-8 pt16 pb16">
                            <span>© 2026 晋江市奥登科鞋业有限公司 · 奥登科户外 AUDENKO OUTDOOR</span>
                        </div>
                        <div class="col-lg-4 text-lg-end pt16 pb16">
                            <span class="text-muted">本站为演示站点，产品与数据仅供参考</span>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </xpath>
</data>'''

rpc('ir.ui.view', 'write', [[2372], {'arch_db': FOOTER_ARCH}])
print('页脚已品牌化 ✓')

# ---------- 2. Odoo shell：翻译重载 ----------
from bt_exec import BTExec
ex = BTExec()
sh = ("echo \"wiz = env['base.language.install'].create({'lang_ids': [(6, 0, [12])], 'overwrite': True}); "
      "wiz.lang_install(); env.cr.commit(); print('TRANS_OK')\" | "
      "/opt/odoo20/venv/bin/python3 /opt/odoo20/odoo-bin shell -c /etc/odoo20.conf -d benson --no-http")
out = ex.run(sh, timeout=280, name='adk-trans')
print('翻译重载:', 'OK' if 'TRANS_OK' in out else out[-500:])

# ---------- 3. 重启 Odoo（清资产缓存，让 CSS 重新编译） ----------
ex.run('systemctl restart odoo20', timeout=40, name='adk-restart')
time.sleep(10)
out = ex.run('systemctl is-active odoo20 && ls -la /opt/odoo20/addons/theme_liquid_glass/static/src/css/ && echo RESTART_OK',
             timeout=30, name='adk-restart')
print('重启:', 'OK' if 'RESTART_OK' in out else out[-300:])
print(out[-600:] if 'adk_outdoor.css' not in out else '')
