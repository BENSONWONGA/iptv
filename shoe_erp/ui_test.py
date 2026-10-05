# -*- coding: utf-8 -*-
"""奥登科 ERP 门户 UI 自动化测试 — iOS 26 液态玻璃(3D)样式验证
桌面 1440x900 + 移动 390x844，截图输出 /data/tool/browser_snapshots/
"""
import json, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3333"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/data/tool/browser_snapshots"

R = {"console": [], "api_errors": [], "pages": {}, "styles": {}, "layout": {}, "data": {}}

def log(m):
    print(m, flush=True)

def gs(page, jsobj):
    return page.evaluate("""(selProps) => {
        const out = {};
        for (const [name, [sel, props, pseudo]] of Object.entries(selProps)) {
            const el = document.querySelector(sel);
            if (!el) { out[name] = null; continue; }
            const cs = getComputedStyle(el, pseudo || null);
            const o = {};
            (props || []).forEach(p => o[p] = cs.getPropertyValue(p));
            const r = el.getBoundingClientRect();
            o._box = [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)];
            out[name] = o;
        }
        return out;
    }""", jsobj)

def shot(page, name, full=False):
    p = OUT + "/" + name
    page.screenshot(path=p, full_page=full)
    log("[SHOT] " + p)

def wait_sel(page, sel, timeout, desc):
    t0 = time.time()
    try:
        page.wait_for_selector(sel, timeout=timeout)
        dt = round(time.time() - t0, 1)
        skel = page.locator(".skel").count()
        R["pages"][desc] = {"loaded": True, "wait_s": dt, "skeleton_left": skel}
        log("[OK] " + desc + " loaded in " + str(dt) + "s")
        return True
    except Exception:
        dt = round(time.time() - t0, 1)
        skel = page.locator(".skel").count()
        txt = ""
        try:
            txt = page.locator("#page").inner_text()[:120]
            txt = " ".join(txt.splitlines())
        except Exception:
            pass
        R["pages"][desc] = {"loaded": False, "wait_s": dt, "skeleton_left": skel, "page_text": txt}
        log("[FAIL] " + desc + " not loaded after " + str(dt) + "s: " + txt[:80])
        return False

def overflow_info(page):
    return page.evaluate("""() => ({
        docScrollW: document.documentElement.scrollWidth,
        innerW: window.innerWidth,
        hOverflow: document.documentElement.scrollWidth > window.innerWidth + 1
    })""")

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME,
            args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        page.on("console", lambda m: R["console"].append({"type": m.type, "text": m.text[:200]}) if m.type == "error" else None)
        page.on("pageerror", lambda e: R["console"].append({"type": "pageerror", "text": str(e)[:200]}))
        def on_resp(r):
            if "/api/" in r.url and r.status >= 400:
                R["api_errors"].append({"url": r.url.split("3333")[-1][:120], "status": r.status})
        page.on("response", on_resp)

        # ---------- 1. 登录页 ----------
        page.goto(BASE)
        page.wait_for_selector(".login-panel", timeout=15000)
        time.sleep(1.2)
        shot(page, "01-login-1440.png")
        R["styles"]["login"] = gs(page, {
            "view_bg": [".login-view", ["background-image"]],
            "bg_glows": [".login-bg", ["background-image"]],
            "bg_grid": [".login-bg", ["background-image"], "::after"],
            "panel": [".login-panel", ["border-radius", "backdrop-filter", "background-color", "box-shadow"]],
            "shoe_icon": [".login-brand .nav-ic.big", ["width", "height", "border-radius", "background-image", "box-shadow"]],
            "token_input": ["#login-token", ["background-color", "box-shadow", "border-radius"]],
            "login_btn": ["#login-btn", ["background-image", "border-radius", "color"]],
        })
        log("[STYLE] login checked")

        # ---------- 2. 登录 ----------
        page.fill("#login-token", TOKEN)
        page.click("#login-btn")
        ok = wait_sel(page, ".stat-card", 90000, "dashboard")
        if ok:
            time.sleep(0.6)
            shot(page, "02-workbench-1440.png", full=True)
            R["styles"]["workbench"] = gs(page, {
                "body_bg": ["body", ["background-image"]],
                "sidebar": [".sidebar", ["background-color", "backdrop-filter"]],
                "topbar": [".topbar", ["background-color", "backdrop-filter"]],
                "stat_card1": [".stat-card", ["border-radius", "backdrop-filter", "background-color", "box-shadow"]],
                "fb_dot_done": [".fb-chip.done .fb-dot", ["background-image", "box-shadow"]],
                "fb_dot_run": [".fb-chip.run .fb-dot", ["background-image", "box-shadow"]],
            })
            R["data"]["workbench"] = page.evaluate("""() => ({
                statLabels: [...document.querySelectorAll('.stat-label')].map(e => e.textContent.trim()),
                statValues: [...document.querySelectorAll('.stat-value')].map(e => e.textContent.trim()),
                glowCount: document.querySelectorAll('.glow').length,
                navIcons: [...document.querySelectorAll('.nav .nav-ic')].map(e => ({
                    label: e.parentElement.textContent.trim(),
                    w: getComputedStyle(e).width,
                    grad: getComputedStyle(e).backgroundImage.slice(0, 90)
                })),
                flowSteps: [...document.querySelectorAll('.fb-chip')].map(e => e.className.replace('fb-chip','').trim() + ':' + e.querySelector('b').textContent),
                todoItems: document.querySelectorAll('.todo-item').length,
                whChips: document.querySelectorAll('.wh-chip').length
            })""")
            page.hover(".stat-card")
            time.sleep(0.4)
            R["styles"]["stat_hover_transform"] = page.evaluate("getComputedStyle(document.querySelector('.stat-card')).transform")
            page.mouse.move(700, 500)
            R["layout"]["workbench_overflow"] = overflow_info(page)

        # ---------- 3. 指令单中心 ----------
        page.evaluate("location.hash = '#/orders'")
        ok = wait_sel(page, "#page table.tbl tbody tr", 60000, "orders")
        if ok:
            time.sleep(0.5)
            shot(page, "03-orders-1440.png", full=True)
            R["data"]["orders"] = page.evaluate("""() => {
                const rows = [...document.querySelectorAll('#page table.tbl tbody tr')];
                const NL = String.fromCharCode(10);
                return {
                    rowCount: rows.length,
                    firstRow: rows[0] ? rows[0].innerText.split(NL).join(' | ').slice(0, 160) : null,
                    tableCardGlass: getComputedStyle(document.querySelector('#page .card')).backdropFilter
                };
            }""")
            R["layout"]["orders_overflow"] = overflow_info(page)

            # ---------- 4. 抽屉 ----------
            page.click("#page table.tbl tbody tr:first-child")
            okd = wait_sel(page, ".chain-node", 90000, "drawer")
            if okd:
                time.sleep(0.6)
                shot(page, "04-drawer-1440.png")
                R["styles"]["drawer"] = gs(page, {
                    "drawer": [".drawer", ["border-radius", "backdrop-filter", "background-color", "box-shadow", "width"]],
                    "chain_line": [".chain", ["background-image"], "::before"],
                    "node_done": [".chain-node.done", ["background-image"], "::before"],
                    "node_pill": [".chain-node .pill.ok", ["background-color", "box-shadow"]],
                })
                R["data"]["drawer"] = page.evaluate("""() => {
                    const NL = String.fromCharCode(10);
                    return {
                        title: document.querySelector('.drawer-hd h3') ? document.querySelector('.drawer-hd h3').innerText.split(NL).join(' ') : null,
                        nodes: [...document.querySelectorAll('.chain-node')].map(n => ({
                            cls: n.className.replace('chain-node','').trim(),
                            text: n.innerText.split(NL).join(' ').slice(0, 60)
                        }))
                    };
                }""")
                page.keyboard.press("Escape")
                time.sleep(0.4)
                R["data"]["drawer_closed_after_esc"] = page.locator(".drawer").count() == 0

        # ---------- 5. 扫码出入库 ----------
        page.evaluate("location.hash = '#/scan'")
        ok = wait_sel(page, "#scan-input", 10000, "scan-initial")
        if ok:
            time.sleep(0.5)
            shot(page, "05-scan-initial-1440.png")
            R["styles"]["scan_hero"] = gs(page, {
                "hero": [".scan-hero", ["background-image", "backdrop-filter", "border-radius"]],
                "input": ["#scan-input", ["background-color", "border-radius", "padding-left", "box-shadow"]],
                "meta": [".scan-meta", ["color"]],
            })
            page.fill("#scan-input", "6901234500011")
            page.press("#scan-input", "Enter")
            ok2 = wait_sel(page, ".scan-item", 150000, "scan-identified")
            if ok2:
                time.sleep(0.5)
                shot(page, "06-scan-identified-1440.png")
                R["styles"]["scan_item"] = gs(page, {
                    "si_img": [".scan-item .si-img", ["width", "height", "border-radius", "background-image", "box-shadow"]],
                })
                R["data"]["scan"] = page.evaluate("""() => {
                    const NL = String.fromCharCode(10);
                    return {
                        itemText: document.querySelector('.scan-item') ? document.querySelector('.scan-item').innerText.split(NL).join(' | ').slice(0, 160) : null,
                        state: document.querySelector('#scan-state') ? document.querySelector('#scan-state').textContent : null,
                        hasFrom: !!document.querySelector('#scan-from'),
                        hasTo: !!document.querySelector('#scan-to'),
                        hasQty: !!document.querySelector('#scan-qty'),
                        hasFo: !!document.querySelector('#scan-fo')
                    };
                }""")

        # ---------- 6. 生产制造 ----------
        page.evaluate("location.hash = '#/production'")
        ok = wait_sel(page, "#page .grid .card", 60000, "production")
        if ok:
            time.sleep(0.5)
            shot(page, "07-production-1440.png", full=True)
            R["data"]["production"] = page.evaluate("""() => ({
                woCards: document.querySelectorAll('#page .grid .card').length,
                progressFills: [...document.querySelectorAll('#page .grid .card div[style]')].filter(d => d.style.width && d.style.background).map(d => ({w: d.style.width, bg: d.style.background.slice(0, 80)})),
                jobRows: document.querySelectorAll('#page .card table.tbl tbody tr').length
            })""")

        # ---------- 7. 应付对账 ----------
        page.evaluate("location.hash = '#/finance'")
        ok = wait_sel(page, "#page .stat-card", 60000, "finance")
        if ok:
            time.sleep(0.5)
            shot(page, "08-finance-1440.png", full=True)
            R["data"]["finance"] = page.evaluate("""() => {
                const rows = [...document.querySelectorAll('#page .card table.tbl tbody tr')];
                const NL = String.fromCharCode(10);
                return {
                    statLabels: [...document.querySelectorAll('#page .stat-label')].map(e => e.textContent.trim()),
                    statValues: [...document.querySelectorAll('#page .stat-value')].map(e => e.textContent.trim()),
                    reconRows: rows.slice(0, 8).map(r => r.innerText.split(NL).join(' | ').slice(0, 110)),
                    balZeroColor: document.querySelector('.bal-zero') ? getComputedStyle(document.querySelector('.bal-zero')).color : null,
                    invoiceRows: document.querySelectorAll('#page .grid .card table.tbl tbody tr').length
                };
            }""")

        # ---------- 8. 流程链路图 ----------
        page.evaluate("location.hash = '#/flow'")
        ok = wait_sel(page, ".fm-node", 90000, "flowmap")
        if ok:
            time.sleep(0.8)
            shot(page, "09-flowmap-1440.png", full=True)
            R["styles"]["flowmap"] = gs(page, {
                "grid": [".flowmap", ["grid-template-columns"]],
                "step_badge": [".fm-step", ["background-image", "box-shadow"]],
                "node_done": [".fm-node.done", ["background-image", "border-color"]],
                "node_done_badge": [".fm-node.done .fm-step", ["background-image"]],
            })
            R["data"]["flowmap"] = page.evaluate("""() => {
                const badges = [...document.querySelectorAll('.fm-step')];
                const NL = String.fromCharCode(10);
                return {
                    nodeCount: document.querySelectorAll('.fm-node').length,
                    doneCount: document.querySelectorAll('.fm-node.done').length,
                    firstBadge: badges[0] ? badges[0].textContent : null,
                    lastBadge: badges.length ? badges[badges.length - 1].textContent : null,
                    pageHd: document.querySelector('.page-hd h2') ? document.querySelector('.page-hd h2').innerText.split(NL).join(' ') : null
                };
            }""")

        # ---------- 9. 移动端 390px ----------
        ctx.storage_state(path="/tmp/odk_state.json")
        mctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                   storage_state="/tmp/odk_state.json")
        mp = mctx.new_page()
        mp.on("console", lambda m: R["console"].append({"type": m.type + "-mobile", "text": m.text[:200]}) if m.type == "error" else None)
        mp.goto(BASE)
        ok = wait_sel(mp, ".stat-card", 90000, "dashboard-mobile")
        if ok:
            time.sleep(0.6)
            shot(mp, "10-workbench-390.png", full=True)
            R["layout"]["mobile"] = mp.evaluate("""() => {
                const sb = document.querySelector('.sidebar');
                const main = document.querySelector('.main');
                const tb = document.querySelector('.topbar');
                const g = document.querySelector('.grid.g4');
                const crumb = document.querySelector('.crumb');
                return {
                    viewport: window.innerWidth,
                    docScrollW: document.documentElement.scrollWidth,
                    hOverflow: document.documentElement.scrollWidth > window.innerWidth + 1,
                    sidebarW: sb ? Math.round(sb.getBoundingClientRect().width) : null,
                    mainW: main ? Math.round(main.getBoundingClientRect().width) : null,
                    topbarOverflow: tb ? (tb.scrollWidth > tb.clientWidth + 2) : null,
                    statGridCols: g ? getComputedStyle(g).gridTemplateColumns : null,
                    crumbRight: crumb ? Math.round(crumb.getBoundingClientRect().right) : null,
                    statCardW: document.querySelector('.stat-card') ? Math.round(document.querySelector('.stat-card').getBoundingClientRect().width) : null
                };
            }""")
        mctx.close()
        ctx.close()
        browser.close()

    print("===RESULT_JSON===")
    print(json.dumps(R, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    run()
