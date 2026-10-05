# -*- coding: utf-8 -*-
"""Phase2: 修复 MR 字段后重测 dashboard/抽屉/链路图"""
import json, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3333"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/data/tool/browser_snapshots"
R = {"pages": {}, "styles": {}, "data": {}, "layout": {}, "console": []}

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
        R["pages"][desc] = {"loaded": True, "wait_s": dt}
        log("[OK] " + desc + " " + str(dt) + "s")
        return True
    except Exception:
        dt = round(time.time() - t0, 1)
        txt = ""
        try:
            txt = " ".join(page.locator("#page").inner_text()[:120].splitlines())
        except Exception:
            pass
        R["pages"][desc] = {"loaded": False, "wait_s": dt, "page_text": txt}
        log("[FAIL] " + desc + " " + str(dt) + "s")
        return False

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        page.on("console", lambda m: R["console"].append({"type": m.type, "text": m.text[:150]}) if m.type == "error" else None)
        page.on("pageerror", lambda e: R["console"].append({"type": "pageerror", "text": str(e)[:150]}))
        page.goto(BASE)
        page.wait_for_selector(".login-panel", timeout=15000)
        page.fill("#login-token", TOKEN)
        page.click("#login-btn")

        # dashboard
        if wait_sel(page, ".stat-card", 60000, "dashboard"):
            time.sleep(0.8)
            shot(page, "02-workbench-1440.png", full=True)
            R["styles"]["workbench"] = gs(page, {
                "body_bg": ["body", ["background-image"]],
                "sidebar": [".sidebar", ["background-color", "backdrop-filter"]],
                "topbar": [".topbar", ["background-color", "backdrop-filter"]],
                "stat_card1": [".stat-card", ["border-radius", "backdrop-filter", "background-color", "box-shadow"]],
                "fb_dot_done": [".fb-chip.done .fb-dot", ["background-image", "box-shadow"]],
                "fb_dot_run": [".fb-chip.run .fb-dot", ["background-image", "box-shadow"]],
                "fb_arrow": [".fb-arrow", ["color"]],
            })
            R["data"]["workbench"] = page.evaluate("""() => ({
                statLabels: [...document.querySelectorAll('.stat-label')].map(e => e.textContent.trim()),
                statValues: [...document.querySelectorAll('.stat-value')].map(e => e.textContent.trim()),
                glowCount: document.querySelectorAll('.glow').length,
                navIcons: [...document.querySelectorAll('.nav .nav-ic')].map(e => ({
                    label: e.parentElement.textContent.trim(),
                    w: getComputedStyle(e).width,
                    grad: getComputedStyle(e).backgroundImage
                })),
                flowSteps: [...document.querySelectorAll('.fb-chip')].map(e => e.className.replace('fb-chip','').trim() + ':' + e.querySelector('b').textContent),
                todoItems: document.querySelectorAll('.todo-item').length,
                whChips: document.querySelectorAll('.wh-chip').length,
                statGridCols: getComputedStyle(document.querySelector('.grid.g4')).gridTemplateColumns
            })""")
            page.hover(".stat-card")
            time.sleep(0.4)
            R["styles"]["stat_hover_transform"] = page.evaluate("getComputedStyle(document.querySelector('.stat-card')).transform")
            page.mouse.move(720, 500)
            R["layout"]["dashboard_overflow"] = page.evaluate("() => ({docScrollW: document.documentElement.scrollWidth, innerW: window.innerWidth, hOverflow: document.documentElement.scrollWidth > window.innerWidth + 1})")

        # orders + drawer
        page.evaluate("location.hash = '#/orders'")
        if wait_sel(page, "#page table.tbl tbody tr", 60000, "orders"):
            page.click("#page table.tbl tbody tr:first-child")
            if wait_sel(page, ".chain-node", 60000, "drawer"):
                time.sleep(0.8)
                shot(page, "04-drawer-1440.png")
                R["styles"]["drawer"] = gs(page, {
                    "drawer": [".drawer", ["border-radius", "backdrop-filter", "background-color", "box-shadow", "width"]],
                    "mask": [".drawer-mask", ["background-color", "backdrop-filter"]],
                    "chain_line": [".chain", ["background-image"], "::before"],
                    "node_done": [".chain-node.done", ["background-image"], "::before"],
                    "node_pill": [".chain-node .pill.ok", ["background-color", "box-shadow"]],
                    "mono_chip": [".chain-node .btn-sm.ghost", ["background-color", "border-radius", "color"]],
                })
                R["data"]["drawer"] = page.evaluate("""() => {
                    const NL = String.fromCharCode(10);
                    return {
                        title: document.querySelector('.drawer-hd h3') ? document.querySelector('.drawer-hd h3').innerText.split(NL).join(' ') : null,
                        nodeCount: document.querySelectorAll('.chain-node').length,
                        nodes: [...document.querySelectorAll('.chain-node')].map(n => ({
                            cls: n.className.replace('chain-node','').trim(),
                            text: n.innerText.split(NL).join(' ').slice(0, 70)
                        }))
                    };
                }""")
                page.keyboard.press("Escape")
                time.sleep(0.4)
                R["data"]["drawer_closed_after_esc"] = page.locator(".drawer").count() == 0

        # flowmap
        page.evaluate("location.hash = '#/flow'")
        if wait_sel(page, ".fm-node", 60000, "flowmap"):
            time.sleep(0.8)
            shot(page, "09-flowmap-1440.png", full=True)
            R["styles"]["flowmap"] = gs(page, {
                "grid": [".flowmap", ["grid-template-columns"]],
                "step_badge": [".fm-step", ["background-image", "box-shadow"]],
                "node": [".fm-node", ["background-color", "backdrop-filter", "border-radius"]],
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
        ctx.close()
        browser.close()
    print("===RESULT_JSON===")
    print(json.dumps(R, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    run()
