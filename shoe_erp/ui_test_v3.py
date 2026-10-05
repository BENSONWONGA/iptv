# -*- coding: utf-8 -*-
"""
v3 UI 验收测试 —— 现代 SaaS 清爽风（顶部导航 + 分屏登录页）
本地 Playwright + Chrome 直连 http://127.0.0.1:3333

覆盖:
  1. 分屏登录页（46%/54%、品牌蓝渐变、玻璃 logo、34px 大标题、4 条特性、演示令牌预填）
  2. 登录 -> 顶部导航（60px sticky、9 项菜单、图标+文字、当前页浅蓝高亮、右侧搜索/徽章/头像/退出、无侧栏）
  3. 工作台（#F5F7FA 背景、4 张白色统计卡 14px 圆角多层阴影 hover 上浮、14 步进度条）
  4. 指令单中心 + 右侧抽屉（白色、垂直时间线绿点）
  5. 扫码出入库（品牌蓝渐变大卡、白色输入框、6901234500011 识别）
  6. 生产制造 / 应付对账 / 流程链路（白卡、绿渐变进度/徽章）
  7. 390px 响应式（导航仅图标、登录页仅右侧表单区）
  8. 回归（console/pageerror、每页加载时间、骨架屏卡死、横向溢出）

截图: v3-login.png v3-topnav.png v3-dashboard.png v3-orders.png v3-drawer.png
      v3-scan.png v3-production.png v3-finance.png v3-flow.png v3-mobile-nav.png v3-mobile.png
输出: v3_result.json / v3_test.log
"""
import json, re, time, traceback
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "http://127.0.0.1:3333"
DEMO_TOKEN = "77455c7d4b3a8fe:f36c1a4b10e8b5e"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/workspace/shoe_erp"
BARCODE = "6901234500011"

R = {"meta": {}, "login": {}, "topnav": {}, "dashboard": {}, "orders": {}, "drawer": {},
     "scan": {}, "production": {}, "finance": {}, "flow": {}, "mobile": {}, "regression": {},
     "checks": [], "console": [], "net_err": [], "load_times": {}, "errors": {}}
CTX = {"tag": "boot"}

def log(m):
    print(m, flush=True)

def check(phase, name, ok, detail=""):
    ok = bool(ok)
    R["checks"].append({"phase": phase, "name": name, "ok": ok, "detail": str(detail)[:300]})
    log(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else "   --> " + str(detail)[:170]))

# ---------------- 颜色工具 ----------------
RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")

def rgbs(s):
    return [tuple(int(x) for x in m) for m in RGB_RE.findall(s or "")]

def is_blue(c):
    r, g, b = c
    return b >= 100 and b > r + 15 and g < b + 30

def is_green(c):
    r, g, b = c
    return g > 60 and g > r and g > b

def is_purple(c):
    r, g, b = c
    return r > 70 and b > 90 and g < 0.75 * min(r, b)

def has_green(s):
    return any(is_green(c) for c in rgbs(s))

def has_blue(s):
    return any(is_blue(c) for c in rgbs(s))

def any_purple(s):
    return [c for c in rgbs(s) if is_purple(c)]

# ---------------- JS 探针 ----------------
LOGIN_JS = r"""
() => {
  const cs = (sel, prop) => { const el = document.querySelector(sel); return el ? getComputedStyle(el)[prop] : null; };
  const left = document.querySelector('.login-left');
  const lr = left.getBoundingClientRect();
  const logo = document.querySelector('.ll-logo');
  const lor = logo.getBoundingClientRect();
  const feats = [...document.querySelectorAll('.ll-feats li')];
  const shadowLayers = (s) => { let d = 0, n = 1; for (const ch of (s || '')) { if (ch === '(') d++; if (ch === ')') d--; if (ch === ',' && d === 0) n++; } return n; };
  return {
    gridCols: cs('.login-view', 'gridTemplateColumns'),
    leftRatio: +(lr.width / innerWidth).toFixed(3),
    leftBg: cs('.login-left', 'backgroundImage'),
    logoBg: cs('.ll-logo', 'backgroundColor'),
    logoBorder: cs('.ll-logo', 'borderTopColor'),
    logoShadow: cs('.ll-logo', 'boxShadow'),
    logoPos: { x: Math.round(lor.x), y: Math.round(lor.y) },
    brandText: (document.querySelector('.ll-brand b') || {}).textContent || '',
    h1Text: ((document.querySelector('.ll-hero h1') || {}).innerText || '').replace(/\s+/g, ' ').trim(),
    h1Size: cs('.ll-hero h1', 'fontSize'),
    h1Color: cs('.ll-hero h1', 'color'),
    featCount: feats.length,
    featHasCheck: feats.map(li => !!li.querySelector('svg use[href="#i-check"]')),
    featTexts: feats.map(li => li.textContent.trim().slice(0, 26)),
    footText: (document.querySelector('.ll-foot') || {}).textContent || '',
    rightBg: cs('.login-right', 'backgroundColor'),
    h2Text: ((document.querySelector('.lr-card h2') || {}).textContent || '').trim(),
    h2Size: cs('.lr-card h2', 'fontSize'),
    baseValue: (document.querySelector('#login-base') || {}).value || '',
    tokenValue: (document.querySelector('#login-token') || {}).value || '',
    tokenType: (document.querySelector('#login-token') || {}).type || '',
    btnText: ((document.querySelector('#login-btn') || {}).textContent || '').trim(),
    btnBg: cs('#login-btn', 'backgroundImage'),
    btnShadow: cs('#login-btn', 'boxShadow'),
    btnShadowLayers: shadowLayers(cs('#login-btn', 'boxShadow')),
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

PRESS_JS = r"""
() => {
  const st = getComputedStyle(document.querySelector('#login-btn'));
  return { transform: st.transform, shadow: st.boxShadow };
}
"""

TOPNAV_JS = r"""
() => {
  const cs = (el, prop) => el ? getComputedStyle(el)[prop] : null;
  const top = document.querySelector('.topnav');
  const links = [...document.querySelectorAll('#nav a')];
  const active = document.querySelector('#nav a.active');
  return {
    navH: cs(top, 'height'), navPos: cs(top, 'position'), navBg: cs(top, 'backgroundColor'),
    brandIcBg: cs(document.querySelector('.brand-ic'), 'backgroundImage'),
    brandIcRadius: cs(document.querySelector('.brand-ic'), 'borderRadius'),
    brandB: (document.querySelector('.brand-txt b') || {}).textContent.trim(),
    brandSpan: (document.querySelector('.brand-txt span') || {}).textContent.trim(),
    menuCount: links.length,
    menuPages: links.map(a => a.dataset.page),
    menuLabels: links.map(a => (a.querySelector('.tn-l') || {}).textContent.trim()),
    menuAllHaveIcon: links.every(a => !!a.querySelector('svg')),
    activePage: active ? active.dataset.page : null,
    activeColor: active ? cs(active, 'color') : null,
    activeBg: active ? cs(active, 'backgroundColor') : null,
    iconColors: links.map(a => cs(a.querySelector('svg'), 'color')),
    searchPlaceholder: (document.querySelector('#global-search') || {}).placeholder || '',
    searchVisible: !!document.querySelector('.top-search'),
    envBadge: (document.querySelector('.env-badge') || {}).textContent.trim(),
    userName: (document.querySelector('#tnav-user-name') || {}).textContent.trim(),
    userRole: (document.querySelector('#tnav-user-role') || {}).textContent.trim(),
    userIcBg: cs(document.querySelector('.tu-ic'), 'backgroundImage'),
    logoutExists: !!document.querySelector('#btn-logout'),
    oldSidebarAbsent: !document.querySelector('.sidebar, .side-nav, aside'),
    appChildren: [...document.querySelector('#app-view').children].map(c => c.className),
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

DASHBOARD_JS = r"""
() => {
  const cs = (el, prop) => el ? getComputedStyle(el)[prop] : null;
  const layers = (s) => { let d = 0, n = 1; for (const ch of (s || '')) { if (ch === '(') d++; if (ch === ')') d--; if (ch === ',' && d === 0) n++; } return n; };
  const cards = [...document.querySelectorAll('#page .stat-card')];
  const chips = [...document.querySelectorAll('#page .fb-chip')];
  const doneDots = [...document.querySelectorAll('#page .fb-chip.done .fb-dot')];
  const blobs = [...document.querySelectorAll('#app-view *')].filter(el => {
    const st = getComputedStyle(el);
    if (st.position !== 'absolute' && st.position !== 'fixed') return false;
    if (el.closest('.stat-card') || el.closest('.fb-step') || el.closest('.drawer')) return false;
    const r = el.getBoundingClientRect();
    return r.width > 200 && r.height > 200 && st.backgroundImage !== 'none';
  }).map(el => el.className || el.tagName);
  return {
    bodyBg: cs(document.body, 'backgroundColor'),
    statCardCount: cards.length,
    statLabels: cards.map(c => (c.querySelector('.stat-label') || {}).textContent.trim()),
    statValues: cards.map(c => (c.querySelector('.stat-value') || {}).innerText.trim()),
    statBgs: cards.map(c => cs(c, 'backgroundColor')),
    statRadius: cards.length ? cs(cards[0], 'borderRadius') : null,
    statShadowLayers: cards.length ? layers(cs(cards[0], 'boxShadow')) : null,
    statShadowSample: cards.length ? cs(cards[0], 'boxShadow') : null,
    statValueSize: cs(document.querySelector('#page .stat-value'), 'fontSize'),
    fbStepCount: document.querySelectorAll('#page .fb-step').length,
    fbDoneCount: chips.filter(c => c.classList.contains('done')).length,
    fbRunCount: chips.filter(c => c.classList.contains('run')).length,
    fbTodoCount: chips.filter(c => !c.classList.contains('done') && !c.classList.contains('run')).length,
    fbDotBgDone: doneDots.length ? cs(doneDots[0], 'backgroundImage') : null,
    fbDotShadowDone: doneDots.length ? cs(doneDots[0], 'boxShadow') : null,
    fbLabels: [...document.querySelectorAll('#page .fb-chip b')].map(b => b.textContent.trim()),
    decorBlobs: blobs,
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

HOVER_JS = r"""
() => {
  const c = document.querySelector('#page .stat-card');
  const st = getComputedStyle(c);
  const layers = (s) => { let d = 0, n = 1; for (const ch of (s || '')) { if (ch === '(') d++; if (ch === ')') d--; if (ch === ',' && d === 0) n++; } return n; };
  return { transform: st.transform, shadow: st.boxShadow, shadowLayers: layers(st.boxShadow) };
}
"""

ORDERS_JS = r"""
() => {
  const rows = [...document.querySelectorAll('#page table.tbl tbody tr')];
  return {
    header: ((document.querySelector('.page-hd h2') || {}).innerText || '').replace(/\s+/g, ' ').trim(),
    rowCount: rows.length,
    firstFo: rows.length ? (rows[0].querySelector('td .mono') || {}).textContent.trim() : null,
    cardBg: getComputedStyle(document.querySelector('#page .card')).backgroundColor,
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

DRAWER_JS = r"""
() => {
  const cs = (el, prop) => el ? getComputedStyle(el)[prop] : null;
  const d = document.querySelector('.drawer');
  const nodes = [...document.querySelectorAll('.drawer .chain-node')];
  const done = document.querySelector('.drawer .chain-node.done');
  return {
    drawerBg: cs(d, 'backgroundColor'),
    drawerWidth: Math.round(d.getBoundingClientRect().width),
    title: ((d.querySelector('.drawer-hd h3') || {}).innerText || '').replace(/\s+/g, ' ').trim().slice(0, 70),
    nodeCount: nodes.length,
    doneCount: nodes.filter(n => n.classList.contains('done')).length,
    runCount: nodes.filter(n => n.classList.contains('run')).length,
    doneDotBg: done ? getComputedStyle(done, '::before').backgroundImage : null,
    doneDotShadow: done ? getComputedStyle(done, '::before').boxShadow : null,
    docLinkCount: d.querySelectorAll('.cn-row').length,
    maskExists: !!document.querySelector('.drawer-mask'),
  };
}
"""

SCAN_JS = r"""
() => {
  const cs = (el, prop) => el ? getComputedStyle(el)[prop] : null;
  const hero = document.querySelector('.scan-hero');
  const inp = document.querySelector('#scan-input');
  return {
    heroBg: cs(hero, 'backgroundImage'),
    heroColor: cs(hero, 'color'),
    heroShadow: cs(hero, 'boxShadow'),
    inputBg: cs(inp, 'backgroundColor'),
    inputColor: cs(inp, 'color'),
    inputFontSize: cs(inp, 'fontSize'),
    inputRadius: cs(inp, 'borderRadius'),
    stateText: (document.querySelector('#scan-state') || {}).textContent.trim(),
    countText: (document.querySelector('#scan-count') || {}).textContent.trim(),
    logCardExists: !!document.querySelector('.scan-log'),
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

SCAN_AFTER_JS = r"""
() => ({
  stateText: (document.querySelector('#scan-state') || {}).textContent.trim(),
  itemText: ((document.querySelector('.scan-item') || {}).innerText || '').replace(/\s+/g, ' ').trim().slice(0, 150),
  pillText: (document.querySelector('.scan-item .pill') || {}).textContent.trim(),
  fromOptions: [...((document.querySelector('#scan-from') || {}).options || [])].map(o => o.text),
  submitBtnText: (document.querySelector('#scan-submit') || {}).textContent.trim(),
})
"""

PRODUCTION_JS = r"""
() => {
  const cs = (el, prop) => el ? getComputedStyle(el)[prop] : null;
  const bars = [...document.querySelectorAll('#page div[style*="linear-gradient(180deg"]')];
  const cards = [...document.querySelectorAll('#page .grid.g2 > .card')];
  const pill = document.querySelector('#page .pill.ok');
  return {
    header: ((document.querySelector('.page-hd h2') || {}).innerText || '').replace(/\s+/g, ' ').trim(),
    woCardCount: cards.length,
    firstCardBg: cards.length ? cs(cards[0], 'backgroundColor') : null,
    firstCardShadow: cards.length ? cs(cards[0], 'boxShadow') : null,
    barCount: bars.length,
    greenBars: bars.filter(b => /rgb\(75, 227, 125\)|#4BE37D/i.test(cs(b, 'backgroundImage'))).length,
    orangeBars: bars.filter(b => /rgb\(255, 194, 74\)|#FFC24A/i.test(cs(b, 'backgroundImage'))).length,
    pillOkCount: document.querySelectorAll('#page .pill.ok').length,
    pillOkSample: pill ? { bg: cs(pill, 'backgroundColor'), color: cs(pill, 'color'), text: pill.textContent.trim() } : null,
    jcRows: document.querySelectorAll('#page table.tbl tbody tr').length,
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

FINANCE_JS = r"""
() => {
  const cs = (el, prop) => el ? getComputedStyle(el)[prop] : null;
  const cards = [...document.querySelectorAll('#page .stat-card')];
  const bz = document.querySelector('.bal-zero');
  const amber = document.querySelector('#page .stat-card.amber .stat-value');
  return {
    header: ((document.querySelector('.page-hd h2') || {}).innerText || '').replace(/\s+/g, ' ').trim(),
    statCount: cards.length,
    statLabels: cards.map(c => (c.querySelector('.stat-label') || {}).textContent.trim()),
    statBgs: cards.map(c => cs(c, 'backgroundColor')),
    amberValueColor: amber ? cs(amber, 'color') : null,
    totalRow: !!document.querySelector('.recon-total'),
    balZeroColor: bz ? cs(bz, 'color') : null,
    balZeroCount: document.querySelectorAll('.bal-zero').length,
    balOpenCount: document.querySelectorAll('.bal-open').length,
    reconRows: document.querySelectorAll('#page table.tbl tbody tr').length,
    pillOkCount: document.querySelectorAll('#page .pill.ok').length,
    pillRunCount: document.querySelectorAll('#page .pill.run').length,
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

FLOW_JS = r"""
() => {
  const cs = (el, prop) => el ? getComputedStyle(el)[prop] : null;
  const nodes = [...document.querySelectorAll('.fm-node')];
  const done = document.querySelector('.fm-node.done');
  const todo = document.querySelector('.fm-node:not(.done) .fm-step');
  return {
    header: ((document.querySelector('.page-hd h2') || {}).innerText || '').replace(/\s+/g, ' ').trim(),
    nodeCount: nodes.length,
    doneCount: nodes.filter(n => n.classList.contains('done')).length,
    nodeBgSample: nodes.length ? cs(nodes[0], 'backgroundColor') : null,
    nodeBorderSample: nodes.length ? cs(nodes[0], 'borderTopColor') : null,
    nodeShadowSample: nodes.length ? cs(nodes[0], 'boxShadow') : null,
    doneBg: done ? cs(done, 'backgroundImage') : null,
    doneStepBadge: done ? cs(done.querySelector('.fm-step'), 'backgroundImage') : null,
    stepBadgeBlue: todo ? cs(todo, 'backgroundImage') : null,
    stepLabels: nodes.map(n => (n.querySelector('.fm-step') || {}).textContent.trim()),
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

MOBILE_NAV_JS = r"""
() => {
  const cs = (el, prop) => el ? getComputedStyle(el)[prop] : null;
  const links = [...document.querySelectorAll('#nav a')];
  const vis = (sel) => { const el = document.querySelector(sel); return el ? el.getBoundingClientRect().width > 0 : false; };
  return {
    vw: innerWidth,
    tnLDisplay: links.map(a => cs(a.querySelector('.tn-l'), 'display')),
    iconsVisible: links.map(a => { const s = a.querySelector('svg'); return s ? s.getBoundingClientRect().width > 0 : false; }),
    brandTxtDisplay: cs(document.querySelector('.brand-txt'), 'display'),
    navH: cs(document.querySelector('.topnav'), 'height'),
    searchDisplay: cs(document.querySelector('.top-search'), 'display'),
    envBadgeDisplay: cs(document.querySelector('.env-badge'), 'display'),
    userDisplay: cs(document.querySelector('.tnav-user'), 'display'),
    logoutVisible: vis('#btn-logout'),
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

MOBILE_LOGIN_JS = r"""
() => {
  const cs = (el, prop) => el ? getComputedStyle(el)[prop] : null;
  const left = document.querySelector('.login-left');
  const right = document.querySelector('.login-right');
  return {
    leftDisplay: cs(left, 'display'),
    leftRectW: Math.round(left.getBoundingClientRect().width),
    rightW: Math.round(right.getBoundingClientRect().width),
    gridCols: cs(document.querySelector('.login-view'), 'gridTemplateColumns'),
    h2Visible: document.querySelector('.lr-card h2').getBoundingClientRect().height > 0,
    formVisible: document.querySelector('#login-btn').getBoundingClientRect().height > 0,
    tokenValue: (document.querySelector('#login-token') || {}).value || '',
    overflow: { scrollW: document.documentElement.scrollWidth, innerW: innerWidth },
  };
}
"""

# ---------------- 主流程 ----------------
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME, headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars", "--force-color-profile=srgb"])
        context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = context.new_page()
        page.set_default_timeout(45000)
        try:
            cdp = context.new_cdp_session(page)
            cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        except Exception as e:
            log("CDP no-cache failed: " + str(e)[:120])

        page.on("console", lambda m: (m.type in ("error", "warning")) and R["console"].append({"ctx": CTX["tag"], "type": m.type, "text": m.text[:250]}))
        page.on("pageerror", lambda e: R["console"].append({"ctx": CTX["tag"], "type": "pageerror", "text": str(e)[:250]}))
        page.on("requestfailed", lambda r: R["net_err"].append({"ctx": CTX["tag"], "url": r.url[:160], "err": str(r.failure)[:160]}))
        page.on("response", lambda r: (r.status >= 400) and R["net_err"].append({"ctx": CTX["tag"], "type": "http", "status": r.status, "url": r.url[:160]}))

        R["meta"] = {"base": BASE, "chrome": CHROME, "viewport_desktop": "1440x900", "viewport_mobile": "390x844",
                     "started": time.strftime("%Y-%m-%d %H:%M:%S")}

        def run_phase(name, fn):
            log("")
            log("===== " + name + " =====")
            t = time.time()
            try:
                fn()
            except Exception as e:
                R["errors"][name] = traceback.format_exc()[:1000]
                log("  [PHASE ERROR] " + name + ": " + str(e)[:220])
            log("  ----- %s done in %.1fs" % (name, time.time() - t))

        def goto_page(tag, expect_skeleton=True, timeout=150000):
            CTX["tag"] = tag
            t0 = time.time()
            if expect_skeleton:
                try:
                    page.wait_for_function("() => !!document.querySelector('#page .loading-block')", timeout=6000)
                except PWTimeout:
                    pass
            try:
                page.wait_for_function("() => !document.querySelector('#page .loading-block')", timeout=timeout)
                stuck = False
            except PWTimeout:
                stuck = True
            ms = round((time.time() - t0) * 1000)
            skel_left = page.evaluate("() => document.querySelectorAll('#page .skel').length")
            R["load_times"][tag] = {"ms": ms, "stuck": stuck, "skel_left": skel_left}
            log("  [%s] loaded in %sms stuck=%s skel_left=%s" % (tag, ms, stuck, skel_left))
            return R["load_times"][tag]

        # ---------- 1. 登录页 ----------
        def phase_login_page():
            CTX["tag"] = "login-page"
            page.goto(BASE, wait_until="domcontentloaded")
            page.wait_for_selector("#login-view", timeout=30000)
            page.wait_for_function("() => ((document.querySelector('#login-token') || {}).value || '') !== ''", timeout=10000)
            time.sleep(0.6)
            d = page.evaluate(LOGIN_JS)
            R["login"].update(d)
            check("login", "分屏比例 46%/54%", 0.44 <= d["leftRatio"] <= 0.48, "leftRatio=" + str(d["leftRatio"]) + " cols=" + str(d["gridCols"]))
            check("login", "左侧品牌蓝渐变 #1E74FF->#0E42D2",
                  "linear-gradient" in (d["leftBg"] or "") and (30, 116, 255) in rgbs(d["leftBg"]) and (14, 66, 210) in rgbs(d["leftBg"]),
                  d["leftBg"])
            check("login", "logo 白色玻璃感(半透明白+inset高光)",
                  "rgba(255, 255, 255" in (d["logoBg"] or "") and "inset" in (d["logoShadow"] or ""),
                  str(d["logoBg"]) + " | " + str(d["logoShadow"]))
            check("login", "logo 位于左上角", d["logoPos"]["x"] < 110 and d["logoPos"]["y"] < 110, str(d["logoPos"]))
            check("login", "品牌名「奥登科·鞋业智造」", ("奥登科" in d["brandText"]) and ("鞋业智造" in d["brandText"]), d["brandText"])
            check("login", "大标题文案完整", ("一单到底" in d["h1Text"]) and ("从接单到付款全程数字化" in d["h1Text"]), d["h1Text"])
            check("login", "大标题 34px 白字", d["h1Size"] == "34px" and d["h1Color"] == "rgb(255, 255, 255)", str(d["h1Size"]) + " / " + str(d["h1Color"]))
            check("login", "4 条特性清单且带勾选图标", d["featCount"] == 4 and all(d["featHasCheck"]),
                  str(d["featCount"]) + " " + json.dumps(d["featTexts"], ensure_ascii=False))
            check("login", "左下角版权", ("2026" in d["footText"]) and ("奥登科" in d["footText"]), d["footText"])
            check("login", "右侧白底区", d["rightBg"] == "rgb(255, 255, 255)", d["rightBg"])
            check("login", "「欢迎回来」26px", d["h2Text"] == "欢迎回来" and d["h2Size"] == "26px", str(d["h2Text"]) + " / " + str(d["h2Size"]))
            check("login", "服务地址自动识别", (d["baseValue"] or "").startswith("http://127.0.0.1:3333"), d["baseValue"])
            check("login", "令牌自动填入演示令牌", d["tokenValue"] == DEMO_TOKEN, str(d["tokenValue"])[:40])
            check("login", "令牌明文可见(text 便于核对)", d["tokenType"] == "text", d["tokenType"])
            check("login", "登录按钮文案「登 录」", d["btnText"] == "登 录", repr(d["btnText"]))
            check("login", "按钮品牌蓝渐变", "linear-gradient" in (d["btnBg"] or "") and has_blue(d["btnBg"]), d["btnBg"])
            check("login", "按钮 inset 高光 + 多层阴影", "inset" in (d["btnShadow"] or "") and d["btnShadowLayers"] >= 3,
                  "layers=" + str(d["btnShadowLayers"]))
            check("login", "登录页无横向溢出", d["overflow"]["scrollW"] <= d["overflow"]["innerW"] + 1, str(d["overflow"]))
            time.sleep(0.4)
            page.screenshot(path=OUT + "/v3-login.png")
            log("  [SHOT] v3-login.png")

        # ---------- 2. 登录 + 顶部导航 ----------
        def phase_login_topnav():
            bb = page.locator("#login-btn").bounding_box()
            page.mouse.move(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
            page.mouse.down()
            time.sleep(0.25)
            press = page.evaluate(PRESS_JS)
            R["login"]["press"] = press
            t0 = time.time()
            page.mouse.up()
            CTX["tag"] = "login-submit"
            page.wait_for_selector("#app-view", state="visible", timeout=30000)
            R["load_times"]["login_submit"] = {"ms": round((time.time() - t0) * 1000)}
            CTX["tag"] = "dashboard"
            t1 = time.time()
            page.wait_for_selector("#page .stat-card", timeout=180000)
            R["load_times"]["dashboard"] = {"ms": round((time.time() - t1) * 1000), "stuck": False, "skel_left": 0}
            check("login", "按压 translateY 效果(active)", "matrix" in (press["transform"] or "") and press["transform"] != "none", press["transform"])
            log("  登录提交->应用可见: %sms, ->工作台数据: %sms" % (R["load_times"]["login_submit"]["ms"], R["load_times"]["dashboard"]["ms"]))
            d = page.evaluate(TOPNAV_JS)
            R["topnav"].update(d)
            expected = ["dashboard", "orders", "purchase", "subcontract", "production", "warehouse", "scan", "finance", "flow"]
            check("topnav", "顶部导航 60px 白色", d["navH"] == "60px" and d["navBg"] == "rgb(255, 255, 255)", str(d["navH"]) + " / " + str(d["navBg"]))
            check("topnav", "sticky 置顶", d["navPos"] == "sticky", d["navPos"])
            check("topnav", "logo 蓝色渐变圆角方块", "linear-gradient" in (d["brandIcBg"] or "") and has_blue(d["brandIcBg"]),
                  str(d["brandIcBg"])[:90] + " radius=" + str(d["brandIcRadius"]))
            check("topnav", "双行品牌文字", d["brandB"] == "奥登科鞋业" and d["brandSpan"] == "鞋业智造协同平台", str(d["brandB"]) + " / " + str(d["brandSpan"]))
            check("topnav", "横向菜单 9 项且顺序正确", d["menuCount"] == 9 and d["menuPages"] == expected, str(d["menuPages"]))
            check("topnav", "菜单项均带图标", d["menuAllHaveIcon"])
            check("topnav", "当前页高亮=工作台(浅蓝底 #EAF1FF 蓝字 #0E42D2)",
                  d["activePage"] == "dashboard" and d["activeBg"] == "rgb(234, 241, 255)" and d["activeColor"] == "rgb(14, 66, 210)",
                  str(d["activePage"]) + " bg=" + str(d["activeBg"]) + " color=" + str(d["activeColor"]))
            icons = [tuple(map(int, m)) for m in RGB_RE.findall(" ".join(d["iconColors"]))]
            check("topnav", "导航图标统一蓝色系(无彩虹)", all(is_blue(c) for c in icons) and len(set(d["iconColors"])) <= 2,
                  str(sorted(set(d["iconColors"]))))
            check("topnav", "右侧搜索框+预览版徽章+头像+退出齐全",
                  d["searchVisible"] and ("单号" in d["searchPlaceholder"]) and d["envBadge"] == "预览版" and d["userName"] and d["logoutExists"],
                  "ph=" + str(d["searchPlaceholder"]) + " badge=" + str(d["envBadge"]) + " user=" + str(d["userName"]) + "/" + str(d["userRole"]))
            check("topnav", "无左侧边栏(结构=顶导航+主区)", d["oldSidebarAbsent"] and d["appChildren"] == ["topnav", "page"], str(d["appChildren"]))
            check("topnav", "桌面布局无横向溢出", d["overflow"]["scrollW"] <= d["overflow"]["innerW"] + 1, str(d["overflow"]))
            time.sleep(0.6)
            page.screenshot(path=OUT + "/v3-topnav.png")
            log("  [SHOT] v3-topnav.png")

        # ---------- 3. 工作台 ----------
        def phase_dashboard():
            CTX["tag"] = "dashboard"
            d = page.evaluate(DASHBOARD_JS)
            before_shadow = d["statShadowSample"]
            if d["statCardCount"]:
                page.locator(".stat-card").first.hover()
                time.sleep(0.5)
                hov = page.evaluate(HOVER_JS)
                page.mouse.move(8, 500)
            else:
                hov = {"transform": None, "shadow": None, "shadowLayers": 0}
            R["dashboard"].update(d)
            R["dashboard"]["hover"] = hov
            check("dash", "背景 #F5F7FA 纯净", d["bodyBg"] == "rgb(245, 247, 250)", d["bodyBg"])
            check("dash", "无彩色光斑装饰", d["decorBlobs"] == [], str(d["decorBlobs"]))
            check("dash", "4 张白色统计卡", d["statCardCount"] == 4 and all(bg == "rgb(255, 255, 255)" for bg in d["statBgs"]),
                  str(d["statCardCount"]) + " " + json.dumps(d["statLabels"], ensure_ascii=False))
            check("dash", "统计卡 14px 圆角", d["statRadius"] == "14px", d["statRadius"])
            check("dash", "多层立体阴影(>=3层)", (d["statShadowLayers"] or 0) >= 3, "layers=" + str(d["statShadowLayers"]) + " sample=" + str(d["statShadowSample"])[:90])
            check("dash", "数字大而清晰(33px)", d["statValueSize"] == "33px", str(d["statValueSize"]) + " " + json.dumps(d["statValues"], ensure_ascii=False))
            check("dash", "hover 上浮 translateY(-3px)", "matrix(1, 0, 0, 1, 0, -3)" in (hov["transform"] or ""), "transform=" + str(hov["transform"]))
            check("dash", "hover 阴影增强(大阴影)", (hov["shadowLayers"] or 0) >= 3 and hov["shadow"] != before_shadow, str(hov["shadow"])[:90])
            check("dash", "流程进度条 14 步", d["fbStepCount"] == 14,
                  "steps=" + str(d["fbStepCount"]) + " labels=" + json.dumps(d["fbLabels"], ensure_ascii=False))
            check("dash", "进度圆点全绿(渐变绿3D)",
                  d["fbDoneCount"] == 14 and has_green(d["fbDotBgDone"] or "") and "linear-gradient" in (d["fbDotBgDone"] or ""),
                  "done=" + str(d["fbDoneCount"]) + " run=" + str(d["fbRunCount"]) + " todo=" + str(d["fbTodoCount"]) + " dot=" + str(d["fbDotBgDone"])[:100])
            check("dash", "工作台无横向溢出", d["overflow"]["scrollW"] <= d["overflow"]["innerW"] + 1, str(d["overflow"]))
            time.sleep(0.4)
            page.screenshot(path=OUT + "/v3-dashboard.png")
            log("  [SHOT] v3-dashboard.png")

        # ---------- 4. 指令单中心 + 抽屉 ----------
        def phase_orders_drawer():
            page.click('#nav a[data-page="orders"]')
            ld = goto_page("orders")
            d = page.evaluate(ORDERS_JS)
            R["orders"].update(d)
            check("orders", "订单表格加载完成", d["rowCount"] >= 1 and not ld["stuck"], "rows=" + str(d["rowCount"]) + " load=" + str(ld["ms"]) + "ms firstFo=" + str(d["firstFo"]))
            check("orders", "白色卡片风格", d["cardBg"] == "rgb(255, 255, 255)", d["cardBg"])
            check("orders", "骨架屏未卡死", (not ld["stuck"]) and ld["skel_left"] == 0, str(ld))
            check("orders", "页面无横向溢出", d["overflow"]["scrollW"] <= d["overflow"]["innerW"] + 1, str(d["overflow"]))
            time.sleep(0.4)
            page.screenshot(path=OUT + "/v3-orders.png")
            log("  [SHOT] v3-orders.png")
            CTX["tag"] = "drawer"
            page.locator("#page table.tbl tbody tr").first.click()
            t0 = time.time()
            page.wait_for_selector(".drawer .chain", timeout=150000)
            R["load_times"]["drawer_chain"] = {"ms": round((time.time() - t0) * 1000), "stuck": False, "skel_left": 0}
            time.sleep(0.5)
            dr = page.evaluate(DRAWER_JS)
            R["drawer"].update(dr)
            check("drawer", "右侧抽屉(白色)", dr["drawerBg"] == "rgb(255, 255, 255)", str(dr["drawerBg"]) + " w=" + str(dr["drawerWidth"]))
            check("drawer", "抽屉宽度 ~560px", 500 <= dr["drawerWidth"] <= 620, dr["drawerWidth"])
            check("drawer", "垂直时间线 14 节点", dr["nodeCount"] == 14, "nodes=" + str(dr["nodeCount"]) + " title=" + str(dr["title"]))
            check("drawer", "完成节点绿点(渐变绿)", dr["doneCount"] >= 1 and has_green(dr["doneDotBg"] or ""),
                  "done=" + str(dr["doneCount"]) + " run=" + str(dr["runCount"]) + " dot=" + str(dr["doneDotBg"])[:90])
            check("drawer", "链路单据可穿透点击", dr["docLinkCount"] >= 1, "links=" + str(dr["docLinkCount"]))
            page.screenshot(path=OUT + "/v3-drawer.png")
            log("  [SHOT] v3-drawer.png")
            page.keyboard.press("Escape")
            page.wait_for_function("() => !document.querySelector('.drawer')", timeout=5000)

        # ---------- 5. 扫码出入库 ----------
        def phase_scan():
            page.click('#nav a[data-page="scan"]')
            ld = goto_page("scan", expect_skeleton=False)
            time.sleep(0.4)
            d = page.evaluate(SCAN_JS)
            R["scan"]["before"] = d
            purples = any_purple(d["heroBg"])
            check("scan", "蓝色渐变大卡(品牌蓝 #1668FC)", "linear-gradient" in (d["heroBg"] or "") and (22, 104, 252) in rgbs(d["heroBg"]), str(d["heroBg"])[:110])
            check("scan", "非深紫色(无残留旧配色)", not purples, str(purples))
            check("scan", "白色扫码输入框", d["inputBg"] == "rgb(255, 255, 255)", str(d["inputBg"]) + " radius=" + str(d["inputRadius"]) + " fs=" + str(d["inputFontSize"]))
            page.fill("#scan-input", BARCODE)
            t0 = time.time()
            page.press("#scan-input", "Enter")
            page.wait_for_selector("#scan-detail .scan-item", timeout=150000)
            ms = round((time.time() - t0) * 1000)
            R["load_times"]["scan_recognize"] = {"ms": ms, "stuck": False, "skel_left": 0}
            time.sleep(0.5)
            a = page.evaluate(SCAN_AFTER_JS)
            R["scan"]["after"] = a
            check("scan", "条码 " + BARCODE + " 识别成功", a["stateText"] == "已识别" and a["pillText"] == "已识别", str(a["stateText"]) + " / " + str(a["pillText"]))
            check("scan", "识别出物料 M-FAB-001 并渲染表单", "M-FAB-001" in (a["itemText"] or "") and BARCODE in (a["itemText"] or ""), a["itemText"][:130])
            check("scan", "仓位下拉 5 项(五仓)", len(a["fromOptions"]) == 5, json.dumps(a["fromOptions"], ensure_ascii=False))
            check("scan", "识别耗时 <60s", ms < 60000, str(ms) + "ms")
            check("scan", "页面无横向溢出", d["overflow"]["scrollW"] <= d["overflow"]["innerW"] + 1, str(d["overflow"]))
            page.screenshot(path=OUT + "/v3-scan.png")
            log("  [SHOT] v3-scan.png")

        # ---------- 6. 生产制造 ----------
        def phase_production():
            page.click('#nav a[data-page="production"]')
            ld = goto_page("production")
            d = page.evaluate(PRODUCTION_JS)
            R["production"].update(d)
            pill_ok = (d["pillOkCount"] >= 1) and d["pillOkSample"] and has_green(d["pillOkSample"]["bg"] or "")
            check("prod", "工单卡片白色风格", d["woCardCount"] >= 1 and d["firstCardBg"] == "rgb(255, 255, 255)",
                  str(d["woCardCount"]) + " bg=" + str(d["firstCardBg"]))
            check("prod", "卡片立体阴影", (d["firstCardShadow"] or "") != "none" and (d["firstCardShadow"] or "") != "", str(d["firstCardShadow"])[:80])
            check("prod", "绿色渐变进度条(完成工单)", d["greenBars"] >= 1, "green=" + str(d["greenBars"]) + " orange=" + str(d["orangeBars"]) + " total=" + str(d["barCount"]))
            check("prod", "状态徽章正常(绿色已提交)", pill_ok, str(d["pillOkSample"]))
            check("prod", "骨架屏未卡死", (not ld["stuck"]) and ld["skel_left"] == 0, str(ld))
            check("prod", "页面无横向溢出", d["overflow"]["scrollW"] <= d["overflow"]["innerW"] + 1, str(d["overflow"]))
            time.sleep(0.5)
            page.screenshot(path=OUT + "/v3-production.png", full_page=True)
            log("  [SHOT] v3-production.png")

        # ---------- 7. 应付对账 ----------
        def phase_finance():
            page.click('#nav a[data-page="finance"]')
            ld = goto_page("finance")
            d = page.evaluate(FINANCE_JS)
            R["finance"].update(d)
            bz_green = d["balZeroCount"] >= 1 and d["balZeroColor"] and any(is_green(c) for c in rgbs(d["balZeroColor"]))
            check("fin", "3 张统计卡(白底)", d["statCount"] == 3 and all(bg == "rgb(255, 255, 255)" for bg in d["statBgs"]),
                  str(d["statCount"]) + " " + json.dumps(d["statLabels"], ensure_ascii=False))
            check("fin", "厂商对账合计行", d["totalRow"] and d["reconRows"] >= 2, "rows=" + str(d["reconRows"]))
            check("fin", "结平余额绿色标识(bal-zero)", bz_green, str(d["balZeroColor"]) + " count=" + str(d["balZeroCount"]))
            check("fin", "骨架屏未卡死", (not ld["stuck"]) and ld["skel_left"] == 0, str(ld))
            check("fin", "页面无横向溢出", d["overflow"]["scrollW"] <= d["overflow"]["innerW"] + 1, str(d["overflow"]))
            time.sleep(0.5)
            page.screenshot(path=OUT + "/v3-finance.png", full_page=True)
            log("  [SHOT] v3-finance.png")

        # ---------- 8. 流程链路 ----------
        def phase_flow():
            page.click('#nav a[data-page="flow"]')
            ld = goto_page("flow")
            d = page.evaluate(FLOW_JS)
            R["flow"].update(d)
            check("flow", "14 个链路节点", d["nodeCount"] == 14, "nodes=" + str(d["nodeCount"]))
            check("flow", "白色卡片节点", (d["nodeBgSample"] == "rgb(255, 255, 255)") or ("linear-gradient" in (d["doneBg"] or "")),
                  str(d["nodeBgSample"]) + " doneBg=" + str(d["doneBg"])[:80])
            check("flow", "完成节点绿徽章(渐变绿)", d["doneCount"] >= 1 and has_green(d["doneStepBadge"] or ""),
                  "done=" + str(d["doneCount"]) + " badge=" + str(d["doneStepBadge"])[:90])
            check("flow", "未完成节点品牌蓝渐变徽章", has_blue(d["stepBadgeBlue"] or ""), str(d["stepBadgeBlue"])[:90])
            check("flow", "节点立体阴影", (d["nodeShadowSample"] or "") not in ("", "none"), str(d["nodeShadowSample"])[:80])
            check("flow", "骨架屏未卡死", (not ld["stuck"]) and ld["skel_left"] == 0, str(ld))
            check("flow", "页面无横向溢出", d["overflow"]["scrollW"] <= d["overflow"]["innerW"] + 1, str(d["overflow"]))
            time.sleep(0.6)
            page.screenshot(path=OUT + "/v3-flow.png", full_page=True)
            log("  [SHOT] v3-flow.png")

        # ---------- 9. 390px 响应式 ----------
        def phase_mobile():
            CTX["tag"] = "mobile"
            page.set_viewport_size({"width": 390, "height": 844})
            time.sleep(0.9)
            m = page.evaluate(MOBILE_NAV_JS)
            R["mobile"]["nav"] = m
            check("mobile", "视口 390px", m["vw"] == 390, m["vw"])
            check("mobile", "顶部导航只显示图标(文字隐藏)", all(x == "none" for x in m["tnLDisplay"]) and all(m["iconsVisible"]),
                  "tnL=" + str(sorted(set(m["tnLDisplay"]))) + " icons=" + str(m["iconsVisible"]))
            check("mobile", "品牌双行文字隐藏", m["brandTxtDisplay"] == "none", m["brandTxtDisplay"])
            check("mobile", "搜索/徽章/用户区隐藏(<=720px)",
                  m["searchDisplay"] == "none" and m["envBadgeDisplay"] == "none" and m["userDisplay"] == "none",
                  str(m["searchDisplay"]) + "/" + str(m["envBadgeDisplay"]) + "/" + str(m["userDisplay"]))
            check("mobile", "退出按钮仍可见", m["logoutVisible"])
            check("mobile", "移动端无横向溢出", m["overflow"]["scrollW"] <= m["overflow"]["innerW"] + 1, str(m["overflow"]))
            time.sleep(0.4)
            page.screenshot(path=OUT + "/v3-mobile-nav.png")
            log("  [SHOT] v3-mobile-nav.png")
            page.click("#btn-logout")
            page.wait_for_function("() => document.querySelector('#app-view').hidden === true", timeout=10000)
            time.sleep(0.7)
            ml = page.evaluate(MOBILE_LOGIN_JS)
            R["mobile"]["login"] = ml
            check("mobile", "登录页只显示右侧表单区(左侧隐藏)", ml["leftDisplay"] == "none" and ml["leftRectW"] == 0 and ml["h2Visible"],
                  str(ml["leftDisplay"]) + " w=" + str(ml["leftRectW"]) + " rightW=" + str(ml["rightW"]))
            check("mobile", "表单与演示令牌仍可用", ml["formVisible"] and ml["tokenValue"] == DEMO_TOKEN, str(ml["tokenValue"])[:30])
            check("mobile", "移动登录页无横向溢出", ml["overflow"]["scrollW"] <= ml["overflow"]["innerW"] + 1, str(ml["overflow"]))
            time.sleep(0.3)
            page.screenshot(path=OUT + "/v3-mobile.png")
            log("  [SHOT] v3-mobile.png")

        # ---------- 10. 回归汇总 ----------
        def phase_regression():
            errors = [c for c in R["console"] if c["type"] in ("error", "pageerror")]
            warnings = [c for c in R["console"] if c["type"] == "warning"]
            stuck = {k: v for k, v in R["load_times"].items() if v.get("stuck") or v.get("skel_left")}
            R["regression"] = {"console": R["console"], "net_errors": R["net_err"], "load_times": R["load_times"]}
            check("reg", "全程无 console.error", len([c for c in errors if c["type"] == "error"]) == 0, json.dumps(errors[:3], ensure_ascii=False))
            check("reg", "全程无 pageerror", len([c for c in errors if c["type"] == "pageerror"]) == 0, json.dumps([c for c in errors if c["type"] == "pageerror"][:3], ensure_ascii=False))
            check("reg", "无失败网络请求(>=400/failed)", len(R["net_err"]) == 0, json.dumps(R["net_err"][:3], ensure_ascii=False))
            check("reg", "无骨架屏卡死", not stuck, str(stuck))

        run_phase("P1 登录页", phase_login_page)
        run_phase("P2 登录+顶部导航", phase_login_topnav)
        run_phase("P3 工作台", phase_dashboard)
        run_phase("P4 指令单中心+抽屉", phase_orders_drawer)
        run_phase("P5 扫码出入库", phase_scan)
        run_phase("P6 生产制造", phase_production)
        run_phase("P7 应付对账", phase_finance)
        run_phase("P8 流程链路", phase_flow)
        run_phase("P9 390px 响应式", phase_mobile)
        run_phase("P10 回归汇总", phase_regression)

        R["meta"]["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        R["meta"]["final_url"] = page.url
        try:
            context.close()
        except Exception:
            pass
        browser.close()

    with open(OUT + "/v3_result.json", "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1)

    passed = sum(1 for c in R["checks"] if c["ok"])
    failed = [c for c in R["checks"] if not c["ok"]]
    log("")
    log("==================== SUMMARY ====================")
    log("checks: %d PASS / %d FAIL" % (passed, len(failed)))
    for c in failed:
        log("  FAIL [%s] %s | %s" % (c["phase"], c["name"], c["detail"][:160]))
    if R["errors"]:
        log("phase errors: " + json.dumps(list(R["errors"].keys()), ensure_ascii=False))
    log("load_times: " + json.dumps(R["load_times"], ensure_ascii=False))
    log("console(all levels collected): " + json.dumps(R["console"], ensure_ascii=False)[:600])
    log("net_errors: " + json.dumps(R["net_err"], ensure_ascii=False)[:400])
    log("result json -> " + OUT + "/v3_result.json")

if __name__ == "__main__":
    main()
