# -*- coding: utf-8 -*-
# v4 深色主题「工厂驾驶舱」验收 —— 本地 Playwright + Chrome 直连 http://127.0.0.1:3333（禁用缓存）
import json, os, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3333"
DEMO_TOKEN = "77455c7d4b3a8fe:f36c1a4b10e8b5e"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/workspace/shoe_erp"
BARCODE = "6901234500011"
VW, VH = 1440, 900

AMBER = "rgb(255, 176, 32)"
AMBER_TEXT = "rgb(26, 18, 6)"
INK = "rgb(232, 237, 246)"
SUB = "rgb(139, 150, 168)"
FAINT = "rgb(90, 101, 119)"
BODY_BG = "rgb(12, 17, 24)"
FLOW_STEPS = ["01 接单","02 计划","03 MRP","04 工单","05 采购","06 收料","07 委外","08 发料","09 帮面","10 领料","11 报工","12 入库","13 应付","14 付款"]
PROC_NAMES = ["裁断","针车","成型","画线","品检","包装出货"]

R = {"meta": {}, "login": {}, "focus": {}, "dashboard": {}, "navhover": {}, "orders": {}, "rowhover": {},
     "drawer": {}, "production": {}, "finance": {}, "flow": {}, "scan_before": {}, "scan_after": {},
     "mobile_login": {}, "mobile_nav": {}, "residue": {},
     "regression": {"console": [], "pageerrors": [], "net_err": []},
     "checks": [], "shots": []}


def check(phase, name, ok, detail=""):
    ok = bool(ok)
    R["checks"].append({"phase": phase, "name": name, "ok": ok, "detail": str(detail)[:400]})
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else "  --> " + str(detail)[:240]), flush=True)


def shot(page, name, full=True):
    path = os.path.join(OUT, name)
    page.screenshot(path=path, full_page=full)
    R["shots"].append(path)
    print("[SHOT] " + path, flush=True)


# ---------- JS 探针 ----------
LOGIN_JS = r"""() => {
  const N = s => (s||'').replace(/[\s]+/g,' ');
  const cs = (sel, prop, ps) => { const el = document.querySelector(sel); return el ? getComputedStyle(el, ps||null)[prop] : null; };
  const L = document.querySelector('.login-left'), Rt = document.querySelector('.login-right');
  if (!L || !Rt) return {missing:true};
  const l = L.getBoundingClientRect(), r = Rt.getBoundingClientRect();
  const h1 = document.querySelector('.ll-hero h1'), em = document.querySelector('.ll-hero h1 em');
  const logo = document.querySelector('.ll-logo'), logoSvg = document.querySelector('.ll-logo svg');
  const proc = [...document.querySelectorAll('.ll-process span')].map(s => {
    const i = s.querySelector('i');
    return { no: i?i.textContent:'', text: N(s.textContent), iColor: i?getComputedStyle(i).color:null,
      font: getComputedStyle(s).fontFamily,
      linkW: getComputedStyle(s,'::after').width, linkBg: getComputedStyle(s,'::after').backgroundImage };
  });
  const btn = document.querySelector('#login-btn');
  return {
    bodyBg: getComputedStyle(document.body).backgroundColor,
    bodyGrid: getComputedStyle(document.body,'::before').backgroundImage,
    gridCols: cs('.login-view','gridTemplateColumns'),
    leftRatio: +(l.width/innerWidth).toFixed(4), rightRatio: +(r.width/innerWidth).toFixed(4),
    leftGrid: cs('.login-left','backgroundImage','::before'),
    bandW: cs('.login-left','width','::after'), bandBg: cs('.login-left','backgroundImage','::after'),
    logoBg: logo?getComputedStyle(logo).backgroundImage:null, logoRadius: logo?getComputedStyle(logo).borderRadius:null,
    logoSvgColor: logoSvg?getComputedStyle(logoSvg).color:null,
    h1Size: h1?getComputedStyle(h1).fontSize:null, h1Weight: h1?getComputedStyle(h1).fontWeight:null,
    h1Color: h1?getComputedStyle(h1).color:null,
    emColor: em?getComputedStyle(em).color:null, emShadow: em?getComputedStyle(em).textShadow:null,
    procCount: proc.length, proc,
    formTitle: N((document.querySelector('.lr-card h2')||{}).textContent||''),
    inputBg: cs('.lr-form input','backgroundColor'), inputColor: cs('.lr-form input','color'),
    btnBg: btn?getComputedStyle(btn).backgroundImage:null, btnColor: btn?getComputedStyle(btn).color:null,
    tokenValue: (document.querySelector('#login-token')||{}).value||'',
    tokenType: (document.querySelector('#login-token')||{}).type||'',
    baseValue: (document.querySelector('#login-base')||{}).value||'',
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

FOCUS_JS = r"""() => {
  const i = document.querySelector('#login-token');
  const s = getComputedStyle(i);
  return {focused: document.activeElement === i, borderColor: s.borderColor, boxShadow: s.boxShadow, background: s.backgroundColor};
}"""

DASH_JS = r"""() => {
  const N = s => (s||'').replace(/[\s]+/g,' ');
  const nav = document.querySelector('.topnav');
  const active = document.querySelector('.tnav a.active');
  const hero = document.querySelector('.hero-banner');
  const chips = [...document.querySelectorAll('.hb-chip b')].map(b => ({v: N(b.textContent), color: getComputedStyle(b).color, shadow: getComputedStyle(b).textShadow}));
  const stats = [...document.querySelectorAll('.stat-card')].map(c => {
    const no = c.querySelector('.stat-no'), ic = c.querySelector('.stat-ic'), val = c.querySelector('.stat-value');
    return { no: no?no.textContent:'', noColor: no?getComputedStyle(no).color:null, noPos: no?getComputedStyle(no).position:null,
      noTop: no?getComputedStyle(no).top:null, noRight: no?getComputedStyle(no).right:null,
      icClass: ic?[...ic.classList].filter(x=>x!=='stat-ic').join(','):'',
      icBg: ic?getComputedStyle(ic).backgroundColor:null, icImg: ic?getComputedStyle(ic).backgroundImage:null, icBorder: ic?getComputedStyle(ic).borderTopColor:null,
      label: N((c.querySelector('.stat-label')||{}).textContent||''), value: N((val||{}).textContent||''),
      valSize: val?getComputedStyle(val).fontSize:null, valFont: val?getComputedStyle(val).fontFamily:null };
  });
  const fcNum = document.querySelector('.fc-num');
  const dots = [...document.querySelectorAll('.fb-dot')].map(d => {
    const chip = d.closest('.fb-chip'); const s = getComputedStyle(d);
    return { cls: chip?chip.className:'', bgImg: s.backgroundImage, bgColor: s.backgroundColor, shadow: s.boxShadow };
  });
  return {
    bodyBg: getComputedStyle(document.body).backgroundColor, bodyGrid: getComputedStyle(document.body,'::before').backgroundImage,
    navBg: getComputedStyle(nav).backgroundColor, navBlur: getComputedStyle(nav).backdropFilter,
    navAfterBg: getComputedStyle(nav,'::after').backgroundImage,
    activeColor: active?getComputedStyle(active).color:null, activeSvg: active&&active.querySelector('svg')?getComputedStyle(active.querySelector('svg')).color:null,
    activePage: active?active.dataset.page:null,
    heroBg: hero?getComputedStyle(hero).backgroundImage:null,
    heroAfterH: hero?getComputedStyle(hero,'::after').height:null, heroAfterBg: hero?getComputedStyle(hero,'::after').backgroundImage:null,
    heroH2: N((document.querySelector('.hb-l h2')||{}).textContent||''), heroP: N((document.querySelector('.hb-l p')||{}).textContent||''),
    chipCount: chips.length, chips,
    statCount: stats.length, stats,
    fcNum: fcNum?N(fcNum.textContent):null,
    fcIColor: fcNum&&fcNum.querySelector('i')?getComputedStyle(fcNum.querySelector('i')).color:null,
    fcIShadow: fcNum&&fcNum.querySelector('i')?getComputedStyle(fcNum.querySelector('i')).textShadow:null,
    dotCount: dots.length, doneDots: dots.filter(d=>d.cls.indexOf('done')>=0).length, dots,
    pillOk: N((document.querySelector('.fc-sum .pill.ok')||{}).textContent||''),
    skel: !!document.querySelector('#page .skel'), loadFail: document.body.textContent.includes('加载失败'),
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

NAVHOVER_JS = r"""() => {
  const a = document.querySelector('.tnav a[data-page="purchase"]');
  const svg = a.querySelector('svg');
  return {color: getComputedStyle(a).color, svgColor: getComputedStyle(svg).color};
}"""

ORDERS_JS = r"""() => {
  const row = document.querySelector('table.tbl tbody tr');
  const fo = row ? row.querySelector('td b.mono') : null;
  const h2 = document.querySelector('.page-hd h2');
  return {
    rowCount: document.querySelectorAll('table.tbl tbody tr').length,
    foText: fo ? fo.textContent : null, foColor: fo ? getComputedStyle(fo).color : null,
    tdColor: row && row.children[2] ? getComputedStyle(row.children[2]).color : null,
    subColor: document.querySelector('.page-hd h2 small') ? getComputedStyle(document.querySelector('.page-hd h2 small')).color : null,
    title: h2 && h2.childNodes[0] ? h2.childNodes[0].textContent.trim() : '',
    activeNav: (document.querySelector('.tnav a.active')||{dataset:{}}).dataset.page||'',
    skel: !!document.querySelector('#page .skel'), loadFail: document.body.textContent.includes('加载失败'),
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

ROWHOVER_JS = r"""() => {
  const tr = document.querySelector('table.tbl tbody tr');
  return {tdBg: getComputedStyle(tr.children[1]).backgroundColor};
}"""

DRAWER_JS = r"""() => {
  const d = document.querySelector('.drawer'); if (!d) return {open:false};
  const mask = document.querySelector('.drawer-mask');
  const nodes = [...document.querySelectorAll('.chain-node')];
  const done = nodes.filter(n=>n.classList.contains('done'));
  const first = done[0] ? getComputedStyle(done[0], '::before') : null;
  return {
    open: true, title: (d.querySelector('.drawer-hd h3')||{}).textContent||'',
    drawerBg: getComputedStyle(d).backgroundImage, drawerBorder: getComputedStyle(d).borderLeftColor,
    maskBg: mask?getComputedStyle(mask).backgroundColor:null,
    nodeCount: nodes.length, doneCount: done.length,
    doneDotBg: first?first.backgroundImage:null, doneDotShadow: first?first.boxShadow:null,
    skelInDrawer: !!d.querySelector('.skel'),
    fail: d.textContent.includes('加载失败')
  };
}"""

PROD_JS = r"""() => {
  const cards = [...document.querySelectorAll('#page .grid.g2 > .card')].filter(c => c.querySelector('b.mono'));
  const wos = cards.map(c => {
    const bar = c.querySelector('div[style*="height:10px"] > div');
    const pill = c.querySelector('.pill');
    return { name: c.querySelector('b.mono').textContent, status: pill?N(pill.textContent):'',
      barBg: bar?getComputedStyle(bar).backgroundImage:null, barW: bar?bar.style.width:null };
  });
  function N(s){ return (s||'').replace(/[\s]+/g,' '); }
  return {woCount: wos.length, wos, skel: !!document.querySelector('#page .skel'),
    loadFail: document.body.textContent.includes('加载失败'), overflowX: document.documentElement.scrollWidth - innerWidth};
}"""

FIN_JS = r"""() => {
  const zeros = [...document.querySelectorAll('.bal-zero')];
  const opens = [...document.querySelectorAll('.bal-open')];
  const z = zeros[0];
  return {
    zeroCount: zeros.length, openCount: opens.length,
    zeroTexts: zeros.map(e=>e.textContent.trim()).slice(0,6),
    zeroColor: z?getComputedStyle(z).color:null, zeroShadow: z?getComputedStyle(z).textShadow:null,
    openColor: opens[0]?getComputedStyle(opens[0]).color:null,
    supplierRows: document.querySelectorAll('.card .tbl tbody tr').length,
    skel: !!document.querySelector('#page .skel'), loadFail: document.body.textContent.includes('加载失败'),
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

FLOW_JS = r"""() => {
  const nodes = [...document.querySelectorAll('.fm-node')];
  const data = nodes.map(n => {
    const step = n.querySelector('.fm-step');
    return { step: step?step.textContent.trim():'', done: n.classList.contains('done'),
      nodeBg: getComputedStyle(n).backgroundImage,
      stepColor: step?getComputedStyle(step).color:null, stepBg: step?getComputedStyle(step).backgroundImage:null,
      stepShadow: step?getComputedStyle(step).boxShadow:null };
  });
  return { count: nodes.length, doneCount: data.filter(d=>d.done).length, data,
    headerPill: (document.querySelector('.page-hd .pill')||{}).textContent||'',
    skel: !!document.querySelector('#page .skel'), loadFail: document.body.textContent.includes('加载失败'),
    overflowX: document.documentElement.scrollWidth - innerWidth };
}"""

SCAN_JS = r"""() => {
  const inp = document.querySelector('#scan-input');
  const hero = document.querySelector('.scan-hero');
  return {
    inputBg: inp?getComputedStyle(inp).backgroundColor:null, inputColor: inp?getComputedStyle(inp).color:null,
    heroBg: hero?getComputedStyle(hero).backgroundImage:null, heroBorder: hero?getComputedStyle(hero).borderTopColor:null,
    state: (document.querySelector('#scan-state')||{}).textContent||'',
    skel: !!document.querySelector('#page .skel'), loadFail: document.body.textContent.includes('加载失败'),
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

SCAN_AFTER_JS = r"""() => {
  const img = document.querySelector('.si-img');
  const svg = img ? img.querySelector('svg') : null;
  return {
    state: (document.querySelector('#scan-state')||{}).textContent||'',
    count: (document.querySelector('#scan-count')||{}).textContent||'',
    itemShown: !!img,
    imgBg: img?getComputedStyle(img).backgroundColor:null, imgBorder: img?getComputedStyle(img).borderTopColor:null,
    imgSvg: svg?getComputedStyle(svg).color:null,
    itemCode: (document.querySelector('.scan-item b')||{}).textContent||'',
    pill: (document.querySelector('.scan-item .pill')||{}).textContent||'',
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

MOBILE_LOGIN_JS = r"""() => {
  const L = document.querySelector('.login-left');
  const Rt = document.querySelector('.login-right');
  return {
    leftDisplay: L?getComputedStyle(L).display:null,
    rightVisible: !!Rt && getComputedStyle(Rt).display !== 'none',
    cardVisible: !!document.querySelector('.lr-card'),
    tokenValue: (document.querySelector('#login-token')||{}).value||'',
    vw: innerWidth,
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

MOBILE_NAV_JS = r"""() => {
  const d = s => { const el = document.querySelector(s); return el ? getComputedStyle(el).display : null; };
  return {
    tnl: d('.tn-l'), brandTxt: d('.brand-txt'), topSearch: d('.top-search'), envBadge: d('.env-badge'),
    tnavUser: d('.tnav-user'), tnavOut: d('#btn-logout'),
    navIconCount: [...document.querySelectorAll('.tnav a')].filter(a => getComputedStyle(a).display !== 'none' && a.querySelector('svg')).length,
    heroVisible: !!document.querySelector('.hero-banner'),
    skel: !!document.querySelector('#page .skel'),
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

RESIDUE_JS = r"""() => {
  const P = c => { if (!c || c.indexOf('rgb') !== 0) return null;
    const t = c.replace('rgba(','').replace('rgb(','').replace(')','');
    return t.split(',').map(parseFloat); };
  const bright = [], blueBtns = [], greens = [];
  document.querySelectorAll('.card, .drawer, .stat-card, .fm-node, .hero-banner, .scan-hero, .lr-card, .page-hd .ph-ic, .toast').forEach(el => {
    const s = getComputedStyle(el); const p = P(s.backgroundColor);
    if (p && p.length >= 3) { const op = p.length === 4 ? p[3] : 1;
      if (op > 0.85 && p[0] > 225 && p[1] > 225 && p[2] > 225) bright.push({sel: (el.className||el.tagName).toString().slice(0,60), bg: s.backgroundColor}); }
  });
  document.querySelectorAll('button').forEach(el => {
    const s = getComputedStyle(el); const p = P(s.backgroundColor);
    if (p && p.length >= 3) { const op = p.length === 4 ? p[3] : 1;
      if (op > 0.85 && p[2] > 170 && p[2] > p[0] + 50) blueBtns.push({txt: el.textContent.trim().slice(0,20), bg: s.backgroundColor}); }
    const gi = s.backgroundImage || '';
    if (gi.indexOf('59, 130, 246') >= 0 || gi.indexOf('37, 99, 235') >= 0 || gi.indexOf('96, 165, 250') >= 0) blueBtns.push({txt: el.textContent.trim().slice(0,20), bg: gi.slice(0,90)});
  });
  document.querySelectorAll('.fb-dot, .stat-value, .bal-zero, .fm-step, .pill, [style*="linear-gradient"], .hb-chip b, .fc-num i, .qty').forEach(el => {
    const s = getComputedStyle(el); const all = s.backgroundColor + ' ' + s.color + ' ' + (s.backgroundImage || '');
    if (all.indexOf('22, 163, 74') >= 0 || all.indexOf('34, 197, 94') >= 0 || all.indexOf('16, 185, 129') >= 0 || all.indexOf('22, 188, 130') >= 0)
      greens.push({cls: (el.className || el.tagName).toString().slice(0,50), all: all.slice(0,140)});
  });
  return {bright: bright.slice(0,10), blueBtns: blueBtns.slice(0,10), greens: greens.slice(0,12)};
}"""


def main():
    t0 = time.time()
    print("=== v4 深色主题工厂驾驶舱验收（Playwright + Chrome 直连，缓存禁用） ===", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
            executable_path=CHROME if os.path.exists(CHROME) else None,
            args=["--no-first-run", "--no-default-browser-check", "--disable-dev-shm-usage", "--no-sandbox"])

        def attach(pg, tag):
            pg.on("console", lambda m: (R["regression"]["console"].append({"page": tag, "type": m.type, "text": m.text[:200]}) if m.type in ("error", "warning") else None))
            pg.on("pageerror", lambda e: R["regression"]["pageerrors"].append({"page": tag, "err": str(e)[:300]}))
            pg.on("requestfailed", lambda r: R["regression"]["net_err"].append({"url": r.url[:160], "fail": str(r.failure)[:120]}))

        ctx = browser.new_context(viewport={"width": VW, "height": VH}, locale="zh-CN")
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        print("[i] CDP Network.setCacheDisabled 已启用", flush=True)
        attach(page, "desktop")

        # ---------------- 1. 登录页 ----------------
        print("", flush=True)
        print("--- [1] 登录页（深色分屏 52/48） ---", flush=True)
        page.goto(BASE + "/#/")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".login-view", timeout=15000)
        page.wait_for_timeout(700)
        lg = page.evaluate(LOGIN_JS)
        R["login"] = lg
        check("login", "整体深炭底 #0C1118", lg["bodyBg"] == BODY_BG, lg["bodyBg"])
        check("login", "深色分屏 52/48", abs(lg["leftRatio"] - 0.52) < 0.011 and abs(lg["rightRatio"] - 0.48) < 0.011,
              "left=" + str(lg["leftRatio"]) + " right=" + str(lg["rightRatio"]) + " cols=" + str(lg["gridCols"]))
        check("login", "左侧蓝图网格纹理", "linear-gradient" in (lg["leftGrid"] or "") and "139, 150, 168" in (lg["leftGrid"] or ""), (lg["leftGrid"] or "")[:90])
        check("login", "左区右缘竖向琥珀光带(1px)", lg["bandW"] == "1px" and "255, 176, 32" in (lg["bandBg"] or ""), "w=" + str(lg["bandW"]) + " bg=" + str(lg["bandBg"]))
        check("login", "琥珀金渐变圆角 logo 块 + 深色图标", "linear-gradient" in (lg["logoBg"] or "") and lg["logoSvgColor"] == AMBER_TEXT and lg["logoRadius"] == "12px",
              "bg=" + str(lg["logoBg"]) + " svg=" + str(lg["logoSvgColor"]) + " r=" + str(lg["logoRadius"]))
        check("login", "大标语 44px / 900 权重 / 白色", lg["h1Size"] == "44px" and lg["h1Weight"] == "900" and lg["h1Color"] == INK,
              str(lg["h1Size"]) + "/" + str(lg["h1Weight"]) + "/" + str(lg["h1Color"]))
        check("login", "「一块屏」琥珀色发光字", lg["emColor"] == AMBER and "255, 176, 32" in (lg["emShadow"] or ""),
              "color=" + str(lg["emColor"]) + " shadow=" + str(lg["emShadow"]))
        ok_proc = lg["procCount"] == 6 and all(p["text"] == (("0" + str(i + 1)) + PROC_NAMES[i]) and p["iColor"] == AMBER and "Bahnschrift" in (p["font"] or "") for i, p in enumerate(lg["proc"]))
        ok_link = all(p["linkW"] == "14px" and "linear-gradient" in (p["linkBg"] or "") for p in lg["proc"][:5])
        check("login", "制鞋工序轴 6 胶囊（琥珀序号/等宽字体/渐变连线）", ok_proc and ok_link, "proc=" + json.dumps(lg["proc"], ensure_ascii=False)[:260])
        check("login", "表单标题「进入驾驶舱」", lg["formTitle"] == "进入驾驶舱", lg["formTitle"])
        check("login", "输入框深色半透明 + 浅色文字", lg["inputBg"] == "rgba(255, 255, 255, 0.03)" and lg["inputColor"] == INK,
              "bg=" + str(lg["inputBg"]) + " color=" + str(lg["inputColor"]))
        check("login", "登录按钮琥珀金渐变 + 深色文字 #1A1206（非白字）", "linear-gradient" in (lg["btnBg"] or "") and "255, 196, 85" in (lg["btnBg"] or "") and lg["btnColor"] == AMBER_TEXT,
              "bg=" + str(lg["btnBg"]) + " color=" + str(lg["btnColor"]))
        check("login", "令牌自动预填", lg["tokenValue"] == DEMO_TOKEN, str(lg["tokenValue"])[:24])
        check("login", "登录页无横向溢出", lg["overflowX"] <= 0, lg["overflowX"])
        shot(page, "v4-login.png")

        page.focus("#login-token")
        page.wait_for_timeout(250)
        fo = page.evaluate(FOCUS_JS)
        R["focus"] = fo
        check("login", "输入框聚焦琥珀光圈", fo["borderColor"] == AMBER and "255, 176, 32" in (fo["boxShadow"] or ""),
              "border=" + str(fo["borderColor"]) + " shadow=" + str(fo["boxShadow"]))

        # ---------------- 2. 工作台 ----------------
        print("", flush=True)
        print("--- [2] 登录后工作台 ---", flush=True)
        page.click("#login-btn")
        try:
            page.wait_for_selector(".hero-banner", timeout=60000)
        except Exception:
            pass
        page.wait_for_function("document.querySelector('.hero-banner') && !document.querySelector('#page .skel')", timeout=60000)
        page.wait_for_timeout(700)
        d = page.evaluate(DASH_JS)
        R["dashboard"] = d
        R["residue"]["dashboard"] = page.evaluate(RESIDUE_JS)
        check("dash", "全局深炭底 + 隐约蓝图网格", d["bodyBg"] == BODY_BG and "linear-gradient" in (d["bodyGrid"] or ""), "bg=" + str(d["bodyBg"]) + " grid=" + str(d["bodyGrid"])[:60])
        check("dash", "顶部导航深色半透明毛玻璃", d["navBg"] == "rgba(15, 21, 31, 0.92)" and "blur" in (d["navBlur"] or ""), "bg=" + str(d["navBg"]) + " blur=" + str(d["navBlur"]))
        check("dash", "导航底部琥珀光带线", "255, 176, 32" in (d["navAfterBg"] or ""), str(d["navAfterBg"]))
        check("dash", "菜单 active 琥珀色（文字+图标）", d["activeColor"] == AMBER and d["activeSvg"] == AMBER and d["activePage"] == "dashboard",
              "color=" + str(d["activeColor"]) + " svg=" + str(d["activeSvg"]) + " page=" + str(d["activePage"]))
        page.hover('.tnav a[data-page="purchase"]')
        page.wait_for_timeout(300)
        h = page.evaluate(NAVHOVER_JS)
        R["navhover"] = h
        check("dash", "菜单图标 hover 琥珀色", h["svgColor"] == AMBER, "svg=" + str(h["svgColor"]) + " text=" + str(h["color"]))
        check("dash", "欢迎横幅深色面板 + 右上角琥珀光晕", "radial-gradient" in (d["heroBg"] or "") and "255, 176, 32" in (d["heroBg"] or "") and "linear-gradient" in (d["heroBg"] or ""), (d["heroBg"] or "")[:110])
        check("dash", "横幅底部琥珀渐变刻度线(2px)", d["heroAfterH"] == "2px" and "255, 176, 32" in (d["heroAfterBg"] or ""), "h=" + str(d["heroAfterH"]) + " bg=" + str(d["heroAfterBg"]))
        ok_chip = d["chipCount"] == 3 and all(c["color"] == AMBER for c in d["chips"]) and all("255, 176, 32" in (c["shadow"] or "") for c in d["chips"])
        check("dash", "数字胶囊琥珀色发光数字", ok_chip, "chips=" + json.dumps(d["chips"], ensure_ascii=False)[:200])
        ok_no = [s["no"] for s in d["stats"]] == ["01", "02", "03", "04"]
        ok_no_style = d["statCount"] == 4 and all(s["noColor"] == FAINT and s["noPos"] == "absolute" and s["noTop"] == "14px" and s["noRight"] == "16px" for s in d["stats"])
        check("dash", "4 张统计卡 + 01-04 灰色序号（右上角）", ok_no and ok_no_style, "nos=" + str([s["no"] for s in d["stats"]]) + " color=" + str(d["stats"][0]["noColor"] if d["stats"] else None))
        ok_ic = [s["icClass"] for s in d["stats"]] == ["blue", "cyan", "amber", "green"]
        ok_ic_style = all((s["icImg"] in (None, "none")) and (s["icBg"] or "").startswith("rgba") and s["icBorder"] and s["icBorder"] != "rgba(0, 0, 0, 0)" for s in d["stats"])
        check("dash", "分类色图标块 蓝/青/琥珀/绿（深色底描边非实心）", ok_ic and ok_ic_style,
              "cls=" + str([s["icClass"] for s in d["stats"]]) + " bg=" + str([s["icBg"] for s in d["stats"]]) + " border=" + str([s["icBorder"] for s in d["stats"]]))
        check("dash", "34px 等宽大数字", all(s["valSize"] == "34px" and "Bahnschrift" in (s["valFont"] or "") for s in d["stats"]),
              "size=" + str([s["valSize"] for s in d["stats"]]) + " font=" + str(d["stats"][0]["valFont"] if d["stats"] else None))
        check("dash", "流程卡头部「14 / 14」（14 琥珀发光）", d["fcNum"] == "14 / 14" and d["fcIColor"] == AMBER and "255, 176, 32" in (d["fcIShadow"] or ""),
              "num=" + repr(d["fcNum"]) + " iColor=" + str(d["fcIColor"]) + " shadow=" + str(d["fcIShadow"]))
        done_dots = d["dots"]
        ok_dot = d["dotCount"] == 14 and d["doneDots"] == 14 and all("linear-gradient" in (x["bgImg"] or "") and "255, 196, 85" in x["bgImg"] for x in done_dots if "done" in x["cls"])
        ok_glow = all("255, 176, 32" in (x["shadow"] or "") for x in done_dots if "done" in x["cls"])
        green_dot = any(("22, 163, 74" in (x["bgImg"] or "")) or ("34, 197, 94" in (x["bgImg"] or "")) or ("22, 163, 74" in (x["bgColor"] or "")) for x in done_dots)
        check("dash", "14 步骤圆点琥珀金渐变球（金色外发光，非绿色）", ok_dot and ok_glow and (not green_dot),
              "count=" + str(d["dotCount"]) + " done=" + str(d["doneDots"]) + " sample=" + json.dumps(done_dots[0], ensure_ascii=False)[:150] if done_dots else "no dots")
        check("dash", "工作台无骨架卡死/无加载失败", (not d["skel"]) and (not d["loadFail"]), "skel=" + str(d["skel"]) + " fail=" + str(d["loadFail"]))
        check("dash", "工作台无横向溢出", d["overflowX"] <= 0, d["overflowX"])
        shot(page, "v4-dashboard.png")

        # ---------------- 3. 指令单中心 + 抽屉 ----------------
        print("", flush=True)
        print("--- [3] 指令单中心 + 抽屉 ---", flush=True)
        page.click('.tnav a[data-page="orders"]')
        page.wait_for_selector("#page .page-hd", timeout=45000)
        page.wait_for_function("!document.querySelector('#page .skel')", timeout=45000)
        page.wait_for_timeout(500)
        od = page.evaluate(ORDERS_JS)
        R["orders"] = od
        R["residue"]["orders"] = page.evaluate(RESIDUE_JS)
        check("orders", "指令单中心渲染 + 导航激活", od["title"] == "指令单中心" and od["activeNav"] == "orders" and od["rowCount"] > 0,
              "title=" + str(od["title"]) + " active=" + str(od["activeNav"]) + " rows=" + str(od["rowCount"]))
        check("orders", "表格单据号琥珀色", od["foColor"] == AMBER, "text=" + str(od["foText"]) + " color=" + str(od["foColor"]))
        check("orders", "表格 td 文字 #E8EDF6 对比", od["tdColor"] == INK, od["tdColor"])
        check("orders", "副标题 #8B96A8 可读", od["subColor"] == SUB, od["subColor"])
        check("orders", "指令单页无骨架卡死/无溢出", (not od["skel"]) and od["overflowX"] <= 0, "skel=" + str(od["skel"]) + " ox=" + str(od["overflowX"]))
        page.hover("table.tbl tbody tr")
        page.wait_for_timeout(300)
        rh = page.evaluate(ROWHOVER_JS)
        R["rowhover"] = rh
        check("orders", "表格行 hover 琥珀微光", rh["tdBg"] == "rgba(255, 176, 32, 0.045)", rh["tdBg"])
        page.click("table.tbl tbody tr")
        try:
            page.wait_for_selector(".drawer .chain-node", timeout=60000)
        except Exception:
            pass
        page.wait_for_timeout(900)
        dw = page.evaluate(DRAWER_JS)
        R["drawer"] = dw
        check("drawer", "点行打开深色抽屉", dw["open"] and "linear-gradient" in (dw["drawerBg"] or "") and not dw["fail"],
              "open=" + str(dw["open"]) + " bg=" + str(dw["drawerBg"]) + " fail=" + str(dw["fail"]))
        check("drawer", "链路时间线节点琥珀金圆点", dw["doneCount"] > 0 and "linear-gradient" in (dw["doneDotBg"] or "") and "255, 196, 85" in (dw["doneDotBg"] or "") and "255, 176, 32" in (dw["doneDotShadow"] or ""),
              "nodes=" + str(dw["nodeCount"]) + " done=" + str(dw["doneCount"]) + " bg=" + str(dw["doneDotBg"]) + " shadow=" + str(dw["doneDotShadow"]))
        shot(page, "v4-drawer.png", full=False)
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

        # ---------------- 4. 生产制造 ----------------
        print("", flush=True)
        print("--- [4] 生产制造 ---", flush=True)
        page.click('.tnav a[data-page="production"]')
        page.wait_for_selector("#page .page-hd", timeout=45000)
        page.wait_for_function("!document.querySelector('#page .skel')", timeout=45000)
        page.wait_for_timeout(500)
        pr = page.evaluate(PROD_JS)
        R["production"] = pr
        R["residue"]["production"] = page.evaluate(RESIDUE_JS)
        completed = [w for w in pr["wos"] if "Completed" in (w["status"] or "")]
        ok_completed_amber = all("linear-gradient" in (w["barBg"] or "") and (("219, 138, 0" in w["barBg"]) or ("255, 176, 32" in w["barBg"]) or ("255, 196, 85" in w["barBg"])) for w in completed if w["barBg"])
        no_green_bar = all(not (("22, 163, 74" in (w["barBg"] or "")) or ("34, 197, 94" in (w["barBg"] or "")) or ("16, 185, 129" in (w["barBg"] or ""))) for w in pr["wos"])
        check("production", "工单进度条琥珀金渐变填充（完成态，非绿色）", len(completed) > 0 and ok_completed_amber and no_green_bar,
              "total=" + str(pr["woCount"]) + " completed=" + str(len(completed)) + " bars=" + json.dumps(pr["wos"], ensure_ascii=False)[:300])
        check("production", "生产页无骨架卡死/无溢出", (not pr["skel"]) and pr["overflowX"] <= 0, "skel=" + str(pr["skel"]) + " ox=" + str(pr["overflowX"]))
        shot(page, "v4-production.png")

        # ---------------- 5. 应付对账 ----------------
        print("", flush=True)
        print("--- [5] 应付对账 ---", flush=True)
        page.click('.tnav a[data-page="finance"]')
        page.wait_for_selector("#page .page-hd", timeout=45000)
        page.wait_for_function("!document.querySelector('#page .skel')", timeout=45000)
        page.wait_for_timeout(500)
        fin = page.evaluate(FIN_JS)
        R["finance"] = fin
        R["residue"]["finance"] = page.evaluate(RESIDUE_JS)
        check("finance", "余额 0 琥珀色发光字（非绿色）", fin["zeroCount"] > 0 and fin["zeroColor"] == AMBER and "255, 176, 32" in (fin["zeroShadow"] or ""),
              "zeros=" + str(fin["zeroCount"]) + " texts=" + str(fin["zeroTexts"]) + " color=" + str(fin["zeroColor"]) + " shadow=" + str(fin["zeroShadow"]))
        check("finance", "未结余额红色（无绿色残留）", fin["openCount"] == 0 or fin["openColor"] == "rgb(255, 107, 107)", "open=" + str(fin["openCount"]) + " color=" + str(fin["openColor"]))
        check("finance", "财务页无骨架卡死/无溢出", (not fin["skel"]) and fin["overflowX"] <= 0, "skel=" + str(fin["skel"]) + " ox=" + str(fin["overflowX"]))
        shot(page, "v4-finance.png")

        # ---------------- 6. 流程链路图 ----------------
        print("", flush=True)
        print("--- [6] 流程链路图 ---", flush=True)
        page.click('.tnav a[data-page="flow"]')
        page.wait_for_selector("#page .page-hd", timeout=60000)
        page.wait_for_function("!document.querySelector('#page .skel')", timeout=60000)
        page.wait_for_timeout(800)
        fl = page.evaluate(FLOW_JS)
        R["flow"] = fl
        R["residue"]["flow"] = page.evaluate(RESIDUE_JS)
        steps = [x["step"] for x in fl["data"]]
        ok_steps = steps == FLOW_STEPS
        ok_badge = fl["doneCount"] == 14 and all(x["done"] and x["stepColor"] == AMBER_TEXT and "linear-gradient" in (x["stepBg"] or "") and "255, 196, 85" in (x["stepBg"] or "") for x in fl["data"])
        check("flow", "步骤徽章「01 接单」等琥珀金渐变胶囊（完成态深色字）", ok_steps and ok_badge,
              "steps=" + str(steps) + " done=" + str(fl["doneCount"]) + " sample=" + json.dumps(fl["data"][0], ensure_ascii=False)[:150] if fl["data"] else "empty")
        check("flow", "节点卡深色", fl["count"] > 0 and all("linear-gradient" in (x["nodeBg"] or "") for x in fl["data"]), "bg=" + str(fl["data"][0]["nodeBg"] if fl["data"] else None))
        check("flow", "链路页无骨架卡死/无溢出", (not fl["skel"]) and fl["overflowX"] <= 0, "skel=" + str(fl["skel"]) + " ox=" + str(fl["overflowX"]))
        shot(page, "v4-flow.png")

        # ---------------- 7. 扫码出入库 ----------------
        print("", flush=True)
        print("--- [7] 扫码出入库 ---", flush=True)
        page.click('.tnav a[data-page="scan"]')
        page.wait_for_selector("#scan-input", timeout=45000)
        page.wait_for_timeout(500)
        sc = page.evaluate(SCAN_JS)
        R["scan_before"] = sc
        check("scan", "扫码输入框白底高对比", sc["inputBg"] == "rgb(244, 246, 250)" and sc["inputColor"] != INK,
              "bg=" + str(sc["inputBg"]) + " color=" + str(sc["inputColor"]))
        check("scan", "扫码大卡深色面板 + 琥珀光晕", "radial-gradient" in (sc["heroBg"] or "") and "255, 176, 32" in (sc["heroBg"] or "") and "linear-gradient" in (sc["heroBg"] or ""), (sc["heroBg"] or "")[:110])
        page.fill("#scan-input", BARCODE)
        page.press("#scan-input", "Enter")
        try:
            page.wait_for_function("(document.querySelector('#scan-state')||{}).textContent === '已识别'", timeout=30000)
            ok_scan = True
        except Exception:
            ok_scan = False
        page.wait_for_timeout(700)
        sa = page.evaluate(SCAN_AFTER_JS)
        R["scan_after"] = sa
        R["residue"]["scan"] = page.evaluate(RESIDUE_JS)
        check("scan", "输入 " + BARCODE + " 回车识别 + 物料图标块琥珀描边", ok_scan and sa["state"] == "已识别" and sa["itemShown"] and sa["imgBg"] == "rgba(255, 176, 32, 0.12)" and "255, 176, 32" in (sa["imgBorder"] or "") and sa["imgSvg"] == AMBER,
              "state=" + str(sa["state"]) + " imgBg=" + str(sa["imgBg"]) + " border=" + str(sa["imgBorder"]) + " svg=" + str(sa["imgSvg"]) + " code=" + str(sa["itemCode"]))
        check("scan", "扫码页无溢出", (sc["overflowX"] or 0) <= 0 and (sa["overflowX"] or 0) <= 0, str(sc["overflowX"]) + "/" + str(sa["overflowX"]))
        shot(page, "v4-scan.png")

        # ---------------- 8. 移动端 390px ----------------
        print("", flush=True)
        print("--- [8] 移动端 390px ---", flush=True)
        mctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN")
        mpage = mctx.new_page()
        mcdp = mctx.new_cdp_session(mpage)
        mcdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        attach(mpage, "mobile")
        mpage.goto(BASE + "#/")
        mpage.wait_for_load_state("networkidle")
        mpage.wait_for_selector(".login-view", timeout=15000)
        mpage.wait_for_timeout(600)
        ml = mpage.evaluate(MOBILE_LOGIN_JS)
        R["mobile_login"] = ml
        check("mobile", "390px 登录页只显示表单区（左侧隐藏）", ml["leftDisplay"] == "none" and ml["rightVisible"] and ml["tokenValue"] == DEMO_TOKEN,
              "left=" + str(ml["leftDisplay"]) + " right=" + str(ml["rightVisible"]) + " vw=" + str(ml["vw"]))
        check("mobile", "390px 登录页无横向溢出", ml["overflowX"] <= 0, ml["overflowX"])
        shot(mpage, "v4-mobile-login.png")
        mpage.click("#login-btn")
        try:
            mpage.wait_for_selector(".hero-banner", timeout=60000)
        except Exception:
            pass
        mpage.wait_for_function("document.querySelector('.hero-banner') && !document.querySelector('#page .skel')", timeout=60000)
        mpage.wait_for_timeout(600)
        mn = mpage.evaluate(MOBILE_NAV_JS)
        R["mobile_nav"] = mn
        R["residue"]["mobile"] = mpage.evaluate(RESIDUE_JS)
        check("mobile", "顶部导航图标化（文字/搜索/用户区隐藏）", mn["tnl"] == "none" and mn["topSearch"] == "none" and mn["tnavUser"] == "none" and mn["brandTxt"] == "none" and mn["navIconCount"] >= 8,
              "tnl=" + str(mn["tnl"]) + " search=" + str(mn["topSearch"]) + " user=" + str(mn["tnavUser"]) + " icons=" + str(mn["navIconCount"]))
        check("mobile", "移动端工作台无骨架卡死/无横向溢出", (not mn["skel"]) and mn["overflowX"] <= 0, "skel=" + str(mn["skel"]) + " ox=" + str(mn["overflowX"]))
        shot(mpage, "v4-mobile.png")

        # ---------------- 9. 回归汇总 ----------------
        print("", flush=True)
        print("--- [9] 回归汇总 ---", flush=True)
        errs = [c for c in R["regression"]["console"] if c["type"] == "error"]
        warns = [c for c in R["regression"]["console"] if c["type"] == "warning"]
        check("reg", "0 console error（桌面+移动）", len(errs) == 0, json.dumps(errs[:8], ensure_ascii=False))
        check("reg", "0 pageerror（桌面+移动）", len(R["regression"]["pageerrors"]) == 0, json.dumps(R["regression"]["pageerrors"][:8], ensure_ascii=False))
        bright = [(k, b) for k, v in R["residue"].items() for b in v.get("bright", [])]
        blues = [(k, b) for k, v in R["residue"].items() for b in v.get("blueBtns", [])]
        greens = [(k, g) for k, v in R["residue"].items() for g in v.get("greens", [])]
        check("reg", "无浅色残留（白底卡片/蓝色按钮/绿色状态）", len(bright) == 0 and len(blues) == 0 and len(greens) == 0,
              "bright=" + json.dumps(bright[:3], ensure_ascii=False) + " blue=" + json.dumps(blues[:3], ensure_ascii=False) + " green=" + json.dumps(greens[:3], ensure_ascii=False))
        check("reg", "console warning 数量（信息项）", True, str(len(warns)) + " warnings")
        if len(R["regression"]["net_err"]):
            print("[i] 网络失败请求: " + json.dumps(R["regression"]["net_err"][:5], ensure_ascii=False), flush=True)

        R["meta"] = {"base": BASE, "viewport": str(VW) + "x" + str(VH), "mobile": "390x844", "cache_disabled": True,
                      "chrome": CHROME, "duration_s": round(time.time() - t0, 1)}
        browser.close()


if __name__ == "__main__":
    fatal = None
    try:
        main()
    except Exception as ex:
        import traceback
        fatal = str(ex)
        print("[FATAL] " + fatal, flush=True)
        print(traceback.format_exc(), flush=True)
    with open(os.path.join(OUT, "v4_result.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    n_pass = sum(1 for c in R["checks"] if c["ok"])
    n_fail = len(R["checks"]) - n_pass
    print("", flush=True)
    print("=== 完成: " + str(n_pass) + " PASS / " + str(n_fail) + " FAIL ===", flush=True)
