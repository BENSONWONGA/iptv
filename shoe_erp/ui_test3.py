# -*- coding: utf-8 -*-
"""Phase3: 复验上轮三处修复 + 桌面 1280 回归
Fix1 登录按钮琥珀橙渐变 / Fix2 MRP 字段修复后完整链路 / Fix3 移动端 390px 折叠
"""
import json, traceback
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3333"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/data/tool/browser_snapshots"

R = {"fix1_login": {}, "fix2_mrp": {}, "fix3_mobile": {}, "regression": {}, "console_errors": []}

def log(m):
    print(m, flush=True)

def attach(tag, page):
    def on_console(m):
        if m.type == "error":
            R["console_errors"].append({"ctx": tag, "type": "console.error", "text": m.text[:200]})
    def on_pageerror(e):
        R["console_errors"].append({"ctx": tag, "type": "pageerror", "text": str(e)[:200]})
    page.on("console", on_console)
    page.on("pageerror", on_pageerror)

def no_cache(page):
    try:
        cdp = page.context.new_cdp_session(page)
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        return True
    except Exception as e:
        return "FAIL: " + str(e)[:120]

def shot(page, name, full=False):
    p = OUT + "/" + name
    page.screenshot(path=p, full_page=full)
    log("[SHOT] " + p)

def do_login(page):
    page.goto(BASE)
    page.wait_for_selector(".login-panel", timeout=20000)
    page.fill("#login-token", TOKEN)
    page.click("#login-btn")
    page.wait_for_selector(".stat-card", timeout=90000)
    log("[OK] logged in")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--disable-dev-shm-usage"])

        # =========== A. 桌面 1440: Fix1 登录按钮 + Fix2 MRP 链路 ===========
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        attach("desktop-1440", page)
        R["fix1_login"]["cache_bypass"] = no_cache(page)

        page.goto(BASE)
        page.wait_for_selector(".login-panel", timeout=20000)
        page.wait_for_timeout(700)

        R["fix1_login"]["login_btn"] = page.evaluate("""() => {
            const b = document.querySelector('#login-btn');
            if (!b) return null;
            const cs = getComputedStyle(b);
            const r = b.getBoundingClientRect();
            return { cls: b.className, text: b.textContent.trim(),
                     background: cs.backgroundImage, radius: cs.borderRadius,
                     color: cs.color, w: Math.round(r.width), h: Math.round(r.height) };
        }""")
        lb = R["fix1_login"]["login_btn"] or {}
        bg = lb.get("background", "")
        R["fix1_login"]["amber_gradient_ok"] = ("rgb(255, 194, 74)" in bg and "rgb(255, 159, 10)" in bg and "rgb(240, 127, 0)" in bg)
        R["fix1_login"]["blue_residual"] = ("rgb(10, 132, 255)" in bg or "rgb(61, 158, 255)" in bg or "rgb(0, 105, 219)" in bg)
        shot(page, "login-amber.png")

        page.fill("#login-token", TOKEN)
        page.click("#login-btn")
        page.wait_for_selector(".stat-card", timeout=90000)
        try:
            page.wait_for_selector(".fb-chip", timeout=30000)
        except Exception:
            R["fix2_mrp"]["workbench_error"] = "flowbar (.fb-chip) not found"
        page.wait_for_timeout(800)

        # --- Fix2a 工作台流程进度条 ---
        R["fix2_mrp"]["workbench_flowbar"] = page.evaluate("""() => {
            const chips = [...document.querySelectorAll('.fb-chip')];
            const mrp = chips.find(c => { const b = c.querySelector('b'); return b && b.textContent.trim() === 'MRP'; });
            const dot = mrp ? mrp.querySelector('.fb-dot') : null;
            return {
                total: chips.length,
                doneCount: chips.filter(c => c.classList.contains('done')).length,
                states: chips.map(c => (c.classList.contains('done') ? 'done' : (c.classList.contains('run') ? 'run' : 'todo')) + ':' + (c.querySelector('b') ? c.querySelector('b').textContent.trim() : '?')),
                mrp: mrp ? { cls: mrp.className.replace('fb-chip', '').trim(),
                             dotBg: getComputedStyle(dot).backgroundImage,
                             dotText: dot.textContent.trim() } : null,
                skelLeft: document.querySelectorAll('#page .skel').length
            };
        }""")
        w = R["fix2_mrp"]["workbench_flowbar"]
        mrp = w.get("mrp") or {}
        wbg = mrp.get("dotBg", "")
        R["fix2_mrp"]["workbench_pass"] = bool(
            w.get("total") == 14 and w.get("doneCount") == 14
            and "done" in (mrp.get("cls") or "")
            and "rgb(75, 227, 125)" in wbg and "rgb(31, 168, 72)" in wbg
            and mrp.get("dotText") == "\u2713")
        shot(page, "workbench-flowbar-mrp.png", full=True)

        # --- Fix2b 流程链路图 ---
        page.evaluate("location.hash = '#/flow'")
        page.wait_for_selector(".fm-node", timeout=60000)
        page.wait_for_timeout(800)
        R["fix2_mrp"]["flowmap"] = page.evaluate("""() => {
            const nodes = [...document.querySelectorAll('.fm-node')];
            const mrp = nodes.find(n => { const b = n.querySelector('b'); return b && b.textContent.indexOf('物料申请') >= 0; });
            const base = { total: nodes.length, doneCount: nodes.filter(n => n.classList.contains('done')).length,
                           skelLeft: document.querySelectorAll('#page .skel').length };
            if (!mrp) return Object.assign(base, { found: false });
            const step = mrp.querySelector('.fm-step');
            return Object.assign(base, { found: true,
                mrpCls: mrp.className.replace('fm-node', '').trim(),
                badge: step ? step.textContent.trim() : null,
                badgeBg: step ? getComputedStyle(step).backgroundImage : null,
                borderColor: getComputedStyle(mrp).borderColor,
                docNos: [...mrp.querySelectorAll('.mono')].map(m => m.textContent.trim()) });
        }""")
        f = R["fix2_mrp"]["flowmap"]
        fbg = f.get("badgeBg") or ""
        R["fix2_mrp"]["flowmap_pass"] = bool(
            f.get("found") and "MAT-MR-2026-00001" in (f.get("docNos") or [])
            and "done" in (f.get("mrpCls") or "")
            and "rgb(75, 227, 125)" in fbg and "rgb(31, 168, 72)" in fbg
            and f.get("total") == 14 and f.get("doneCount") == 14)
        shot(page, "flowmap-mrp.png", full=True)

        # --- Fix2c 指令单中心 -> 抽屉 ---
        page.evaluate("location.hash = '#/orders'")
        page.wait_for_selector("#page table.tbl tbody tr", timeout=60000)
        page.wait_for_timeout(500)
        page.click("#page table.tbl tbody tr:first-child")
        page.wait_for_selector(".chain-node", timeout=60000)
        page.wait_for_timeout(800)
        R["fix2_mrp"]["drawer"] = page.evaluate("""() => {
            const nodes = [...document.querySelectorAll('.chain-node')];
            const mrp = nodes.find(n => n.innerText.indexOf('物料申请') >= 0);
            const base = { total: nodes.length, doneCount: nodes.filter(n => n.classList.contains('done')).length };
            if (!mrp) return Object.assign(base, { found: false });
            mrp.scrollIntoView({ block: 'center' });
            const btn = mrp.querySelector('button.mono');
            const before = getComputedStyle(mrp, '::before');
            return Object.assign(base, { found: true,
                mrpCls: mrp.className.replace('chain-node', '').trim(),
                dotBg: before.backgroundImage,
                dotShadow: before.boxShadow,
                btnText: btn ? btn.textContent.trim() : null,
                btnDt: btn ? btn.getAttribute('data-dt') : null,
                text: mrp.innerText.split(String.fromCharCode(10)).join(' ').slice(0, 90) });
        }""")
        d = R["fix2_mrp"]["drawer"]
        dbg = d.get("dotBg") or ""
        R["fix2_mrp"]["drawer_pass"] = bool(
            d.get("found") and "done" in (d.get("mrpCls") or "")
            and "rgb(75, 227, 125)" in dbg and "rgb(31, 168, 72)" in dbg
            and (d.get("btnText") or "") == "MAT-MR-2026-00001"
            and (d.get("btnDt") or "") == "Material Request"
            and d.get("total") == 14 and d.get("doneCount") == 14)
        shot(page, "drawer-mrp.png")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        ctx.close()

        # =========== B. 移动端 390x844 ===========
        ctx2 = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
        page2 = ctx2.new_page()
        attach("mobile-390", page2)
        R["fix3_mobile"]["cache_bypass"] = no_cache(page2)
        do_login(page2)
        page2.wait_for_timeout(800)

        R["fix3_mobile"]["workbench_390"] = page2.evaluate("""() => {
            const sb = document.querySelector('.sidebar');
            const navTs = [...document.querySelectorAll('.nav .nav-t')];
            const icons = [...document.querySelectorAll('.nav .nav-ic')];
            const main = document.querySelector('.main');
            const grid = document.querySelector('.grid.g4');
            const cards = grid ? [...grid.querySelectorAll('.stat-card')] : [];
            return {
                sidebarW: sb ? Math.round(sb.getBoundingClientRect().width) : null,
                navT_total: navTs.length,
                navT_hidden: navTs.filter(t => getComputedStyle(t).display === 'none').length,
                iconCount: icons.length,
                iconsWithGradient: icons.filter(i => (getComputedStyle(i).backgroundImage || '').indexOf('gradient') >= 0).length,
                mainW: main ? Math.round(main.getBoundingClientRect().width) : null,
                docScrollW: document.documentElement.scrollWidth,
                innerW: window.innerWidth,
                hOverflow: document.documentElement.scrollWidth > window.innerWidth,
                statGridCols: grid ? getComputedStyle(grid).gridTemplateColumns : null,
                statCardWs: cards.map(c => Math.round(c.getBoundingClientRect().width)),
                skelLeft: document.querySelectorAll('#page .skel').length
            };
        }""")
        m = R["fix3_mobile"]["workbench_390"]
        cols = len((m.get("statGridCols") or "").split(" "))
        R["fix3_mobile"]["workbench_390_pass"] = bool(
            m.get("sidebarW") == 78
            and m.get("navT_total") == 9 and m.get("navT_hidden") == 9
            and m.get("iconCount") == 9 and m.get("iconsWithGradient") == 9
            and (m.get("mainW") or 0) > 300
            and (m.get("docScrollW") or 999) <= 395 and not m.get("hOverflow")
            and cols == 1)
        shot(page2, "workbench-390-fixed.png", full=True)

        # --- 扫码出入库 390 ---
        page2.evaluate("location.hash = '#/scan'")
        page2.wait_for_selector(".scan-layout", timeout=60000)
        page2.wait_for_timeout(800)
        R["fix3_mobile"]["scan_390"] = page2.evaluate("""() => {
            const sl = document.querySelector('.scan-layout');
            const cols = getComputedStyle(sl).gridTemplateColumns;
            const kids = [...sl.children].map(k => Math.round(k.getBoundingClientRect().width));
            return { cols: cols, colCount: cols.split(' ').length,
                     slW: Math.round(sl.getBoundingClientRect().width),
                     childWs: kids,
                     docScrollW: document.documentElement.scrollWidth,
                     innerW: window.innerWidth,
                     hOverflow: document.documentElement.scrollWidth > window.innerWidth,
                     skelLeft: document.querySelectorAll('#page .skel').length };
        }""")
        s = R["fix3_mobile"]["scan_390"]
        R["fix3_mobile"]["scan_390_pass"] = bool(
            s.get("colCount") == 1 and not s.get("hOverflow") and s.get("skelLeft") == 0)
        shot(page2, "scan-390.png", full=True)
        ctx2.close()

        # =========== C. 桌面 1280 回归 ===========
        ctx3 = browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
        page3 = ctx3.new_page()
        attach("desktop-1280", page3)
        no_cache(page3)
        do_login(page3)
        page3.wait_for_timeout(800)
        pages_to_check = [
            ("dashboard", ".stat-card"),
            ("orders", "#page table.tbl tbody tr"),
            ("scan", ".scan-layout"),
            ("flow", ".fm-node"),
        ]
        for name, sel in pages_to_check:
            page3.evaluate("location.hash = '#/" + name + "'")
            entry = {}
            try:
                page3.wait_for_selector(sel, timeout=60000)
                page3.wait_for_timeout(800)
                entry = page3.evaluate("""() => ({
                    skelLeft: document.querySelectorAll('#page .skel').length,
                    emptyBlocks: document.querySelectorAll('#page .empty').length,
                    docScrollW: document.documentElement.scrollWidth,
                    innerW: window.innerWidth,
                    hOverflow: document.documentElement.scrollWidth > window.innerWidth })""")
                entry["loaded"] = True
            except Exception as e:
                entry = {"loaded": False, "err": str(e)[:120]}
            R["regression"][name] = entry
            shot(page3, "reg-" + name + "-1280.png", full=True)
        ctx3.close()
        browser.close()

try:
    run()
    R["fix1_login"]["PASS"] = bool(R["fix1_login"].get("amber_gradient_ok") and not R["fix1_login"].get("blue_residual"))
    R["fix2_mrp"]["PASS"] = bool(R["fix2_mrp"].get("workbench_pass") and R["fix2_mrp"].get("flowmap_pass") and R["fix2_mrp"].get("drawer_pass"))
    R["fix3_mobile"]["PASS"] = bool(R["fix3_mobile"].get("workbench_390_pass") and R["fix3_mobile"].get("scan_390_pass"))
    reg_pages = [v for k, v in R["regression"].items() if isinstance(v, dict) and "loaded" in v]
    R["regression"]["PASS"] = bool(reg_pages) and all(v.get("loaded") and v.get("skelLeft") == 0 for v in reg_pages)
except Exception:
    R["fatal"] = traceback.format_exc()[-1500:]

print("===RESULT_JSON===")
print(json.dumps(R, ensure_ascii=False, indent=1))
