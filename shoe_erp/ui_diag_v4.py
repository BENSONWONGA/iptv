# -*- coding: utf-8 -*-
# v4 二轮诊断：flow/scan 时序复测 + hover 容差 + bal-zero CSSOM 取证 + 移动端登录溢出定位
import json, os, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3333"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/workspace/shoe_erp"
BARCODE = "6901234500011"
AMBER = "rgb(255, 176, 32)"
AMBER_TEXT = "rgb(26, 18, 6)"
FLOW_STEPS = ["01 接单","02 计划","03 MRP","04 工单","05 采购","06 收料","07 委外","08 发料","09 帮面","10 领料","11 报工","12 入库","13 应付","14 付款"]

D = {"flow": {}, "scan": {}, "hover": {}, "balzero": {}, "mobile": {}, "console": [], "pageerrors": []}

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
    heroBg: hero?getComputedStyle(hero).backgroundImage:null,
    state: (document.querySelector('#scan-state')||{}).textContent||'',
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
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

HOVER_JS = r"""() => {
  const tr = document.querySelector('table.tbl tbody tr');
  return {tdBg: getComputedStyle(tr.children[1]).backgroundColor};
}"""

BALZERO_JS = r"""() => {
  const el = document.querySelector('.bal-zero');
  if (!el) return {found: false};
  const hits = [];
  const walk = rules => { for (const r of (rules||[])) {
    if (r.cssRules) { walk(r.cssRules); continue; }
    if (r.selectorText && r.style && r.style.color && el.matches(r.selectorText)) hits.push({sel: r.selectorText, color: r.style.color});
  } };
  for (const sh of document.styleSheets) { try { walk(sh.cssRules); } catch (e) {} }
  const t = document.querySelector('.recon-total .bal-zero');
  return {found: true, tag: el.tagName, cls: el.className, matched: hits,
    computedColor: getComputedStyle(el).color, computedShadow: getComputedStyle(el).textShadow,
    zeroCount: document.querySelectorAll('.bal-zero').length,
    totalRowZeroColor: t ? getComputedStyle(t).color : null};
}"""

OBS_JS = r"""() => {
  window.__muts = [];
  window.__t0 = Date.now();
  const mo = new MutationObserver(list => {
    for (const m of list) {
      const a = m.addedNodes.length ? ('add:' + Array.from(m.addedNodes).map(n => (n.className || n.tagName || '').toString().slice(0,36)).join('|')) : '';
      const r = m.removedNodes.length ? ('rm:' + Array.from(m.removedNodes).map(n => (n.className || n.tagName || '').toString().slice(0,36)).join('|')) : '';
      window.__muts.push({t: Math.round((Date.now() - window.__t0) / 100) / 10, m: (a || r).slice(0, 90)});
    }
  });
  const pg = document.querySelector('#page');
  if (pg) mo.observe(pg, {childList: true});
  return 'ok';
}"""

MOB_OVER_JS = r"""() => {
  const vw = innerWidth;
  const over = [];
  document.querySelectorAll('body *').forEach(el => {
    const st = getComputedStyle(el); if (st.display === 'none' || st.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    if (r.right > vw + 0.5 || r.width > vw + 0.5) over.push({t: el.tagName, id: el.id, cls: (el.className||'').toString().slice(0,40), w: Math.round(r.width), left: Math.round(r.left), right: Math.round(r.right)});
  });
  const card = document.querySelector('.lr-card');
  const right = document.querySelector('.login-right');
  return {vw, scrollW: document.documentElement.scrollWidth, overflowX: document.documentElement.scrollWidth - vw,
    over: over.slice(0, 15),
    cardW: card ? Math.round(card.getBoundingClientRect().width) : null,
    cardMaxW: card ? getComputedStyle(card).maxWidth : null,
    rightW: right ? Math.round(right.getBoundingClientRect().width) : null,
    rightPad: right ? getComputedStyle(right).padding : null,
    gridCols: getComputedStyle(document.querySelector('.login-view')).gridTemplateColumns};
}"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,
            executable_path=CHROME if os.path.exists(CHROME) else None,
            args=["--no-first-run", "--no-default-browser-check", "--disable-dev-shm-usage", "--no-sandbox"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        page.on("console", lambda m: D["console"].append({"type": m.type, "text": m.text[:160]}))
        page.on("pageerror", lambda e: D["pageerrors"].append(str(e)[:300]))
        page.goto(BASE + "#/")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".login-view", timeout=15000)
        page.click("#login-btn")
        try:
            page.wait_for_selector(".hero-banner", timeout=90000)
        except Exception:
            pass
        page.wait_for_function("document.querySelector('.hero-banner') && !document.querySelector('#page .skel')", timeout=90000)
        page.wait_for_timeout(500)
        print("[i] 登录完成", flush=True)

        # ---- flow 充分等待 ----
        t0 = time.time()
        page.click('.tnav a[data-page="flow"]')
        page.wait_for_function("location.hash === '#/flow'", timeout=10000)
        page.wait_for_selector("#page .fm-node", timeout=150000)
        page.wait_for_timeout(700)
        fl = page.evaluate(FLOW_JS)
        fl["render_s"] = round(time.time() - t0, 1)
        D["flow"] = fl
        steps = [x["step"] for x in fl["data"]]
        ok_steps = steps == FLOW_STEPS
        ok_badge = fl["count"] == 14 and fl["doneCount"] == 14 and all(x["done"] and x["stepColor"] == AMBER_TEXT and "linear-gradient" in (x["stepBg"] or "") and "255, 196, 85" in (x["stepBg"] or "") for x in fl["data"])
        ok_node = fl["count"] > 0 and all("linear-gradient" in (x["nodeBg"] or "") for x in fl["data"])
        print("[FLOW] render_s=" + str(fl["render_s"]) + " steps_ok=" + str(ok_steps) + " badge_ok=" + str(ok_badge) + " node_dark=" + str(ok_node) + " count=" + str(fl["count"]) + " done=" + str(fl["doneCount"]) + " skel=" + str(fl["skel"]) + " ox=" + str(fl["overflowX"]), flush=True)
        if fl["data"]:
            print("[FLOW] sample=" + json.dumps(fl["data"][0], ensure_ascii=False)[:220], flush=True)
        page.screenshot(path=os.path.join(OUT, "v4-flow.png"), full_page=True)
        print("[SHOT] v4-flow.png", flush=True)

        # ---- scan（flow 已稳定后）----
        page.evaluate(OBS_JS)
        t1 = time.time()
        page.click('.tnav a[data-page="scan"]')
        page.wait_for_function("location.hash === '#/scan'", timeout=10000)
        page.wait_for_selector("#scan-input", timeout=45000)
        page.wait_for_timeout(500)
        sc = page.evaluate(SCAN_JS)
        page.fill("#scan-input", BARCODE)
        page.press("#scan-input", "Enter")
        try:
            page.wait_for_function("(document.querySelector('#scan-state')||{}).textContent === '已识别'", timeout=120000)
            ok = True
        except Exception:
            ok = False
        page.wait_for_timeout(700)
        sa = page.evaluate(SCAN_AFTER_JS)
        muts = page.evaluate("() => (window.__muts || [])")
        sa["scan_s"] = round(time.time() - t1, 1)
        D["scan"] = {"before": sc, "after": sa, "recognized": ok, "mutations": muts}
        ok_item = sa["itemShown"] and sa["imgBg"] == "rgba(255, 176, 32, 0.12)" and "255, 176, 32" in (sa["imgBorder"] or "") and sa["imgSvg"] == AMBER
        print("[SCAN] recognized=" + str(ok) + " scan_s=" + str(sa["scan_s"]) + " state=" + repr(sa["state"]) + " item_ok=" + str(ok_item) + " imgBg=" + str(sa["imgBg"]) + " border=" + str(sa["imgBorder"]) + " svg=" + str(sa["imgSvg"]) + " code=" + str(sa["itemCode"]), flush=True)
        print("[SCAN] mutations=" + json.dumps(muts, ensure_ascii=False)[:500], flush=True)
        page.screenshot(path=os.path.join(OUT, "v4-scan.png"), full_page=True)
        print("[SHOT] v4-scan.png", flush=True)

        # ---- orders hover 容差 ----
        page.click('.tnav a[data-page="orders"]')
        page.wait_for_function("location.hash === '#/orders'", timeout=10000)
        page.wait_for_selector("#page .page-hd", timeout=45000)
        page.wait_for_function("!document.querySelector('#page .skel')", timeout=45000)
        page.wait_for_timeout(400)
        page.hover("table.tbl tbody tr")
        page.wait_for_timeout(300)
        rh = page.evaluate(HOVER_JS)
        D["hover"] = rh
        ok_hover = "255, 176, 32" in (rh["tdBg"] or "")
        print("[HOVER] tdBg=" + str(rh["tdBg"]) + " amber_tint=" + str(ok_hover), flush=True)

        # ---- finance bal-zero CSSOM ----
        page.click('.tnav a[data-page="finance"]')
        page.wait_for_function("location.hash === '#/finance'", timeout=10000)
        page.wait_for_function("!document.querySelector('#page .skel')", timeout=45000)
        page.wait_for_timeout(500)
        bz = page.evaluate(BALZERO_JS)
        D["balzero"] = bz
        print("[BALZERO] " + json.dumps(bz, ensure_ascii=False)[:700], flush=True)

        # ---- 移动端 390 登录页溢出定位 ----
        mctx = browser.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN")
        mpage = mctx.new_page()
        mcdp = mctx.new_cdp_session(mpage)
        mcdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        mpage.goto(BASE + "#/")
        mpage.wait_for_load_state("networkidle")
        mpage.wait_for_selector(".login-view", timeout=15000)
        mpage.wait_for_timeout(600)
        mo = mpage.evaluate(MOB_OVER_JS)
        D["mobile"] = mo
        print("[MOB-OVER] " + json.dumps(mo, ensure_ascii=False)[:1000], flush=True)
        mpage.screenshot(path=os.path.join(OUT, "v4-mobile-login.png"))
        print("[SHOT] v4-mobile-login.png (viewport)", flush=True)

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
    with open(os.path.join(OUT, "v4_diag_result.json"), "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1, default=str)
    print("[DONE] 诊断结果已保存 v4_diag_result.json; console=" + str(len(D["console"])) + " pageerrors=" + str(len(D["pageerrors"])), flush=True)
