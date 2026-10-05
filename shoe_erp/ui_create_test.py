# -*- coding: utf-8 -*-
"""开单功能端到端测试：在浏览器 UI 里真实创建四类单据（指令单/采购单/委外单/付款），
验证表单 → 提交 → toast → 列表刷新全链路，并输出创建的单号供清理。"""
import json
import time

from playwright.sync_api import sync_playwright

BASE = "http://220.162.99.166:88/odk"
PORTAL_TOKEN = "0c72b5c60d05fcc:e815d3027f553b1"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/workspace/shoe_erp"

R = {"checks": [], "created": [], "console_errors": [], "page_errors": []}


def check(name, ok, detail=""):
    ok = bool(ok)
    R["checks"].append({"name": name, "ok": ok, "detail": str(detail)[:200]})
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else "  --> " + str(detail)[:200]), flush=True)


def wait_toast(page, key=None, timeout=90000):
    """轮询等待一条「新出现且可见」的 toast，返回其文本。
    （toast 隐藏后文本残留，只看可见状态可避免误读上一单的旧提示）"""
    t0 = time.time()
    while time.time() - t0 < timeout / 1000:
        txt = page.evaluate("""() => { const t = document.querySelector('#toast');
            return (t && !t.hidden) ? t.textContent : ''; }""")
        if txt:
            return txt
        page.wait_for_timeout(250)
    return ""


def clear_toast(page):
    page.evaluate("() => { const t = document.querySelector('#toast'); if (t) t.hidden = true; }")


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True,
                                args=["--proxy-server=http://127.0.0.1:18080", "--no-sandbox", "--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.on("console", lambda m: R["console_errors"].append(str(m.text)[:200]) if m.type == "error" else None)
    page.on("pageerror", lambda e: R["page_errors"].append(str(e)[:200]))

    page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("#login-btn", timeout=20000)
    page.click("#login-btn")
    page.wait_for_selector(".hero-banner", timeout=40000)
    print("[i] 已登录", flush=True)

    # ---- 1) 新建指令单（销售订单） ----
    page.evaluate("location.hash='#/orders'")
    page.wait_for_selector(".tbl tbody tr", timeout=30000)
    page.click("button.btn-amber")  # ＋ 新建指令单
    page.wait_for_selector("#nf-submit", timeout=30000)
    page.wait_for_selector("#nf-customer option", state="attached", timeout=20000)
    page.fill("#nf-fo_no", "TEST-UI-001")
    page.select_option("#nf-item_code", "FG-A001-40-BK")
    page.fill("#nf-qty", "30")
    clear_toast(page)
    page.click("#nf-submit")
    toast = wait_toast(page)
    check("新建指令单 toast", "已创建并提交" in toast, toast)
    so_name = page.evaluate("""() => {
        const m = ((document.querySelector('#toast')||{}).textContent||'').match(/SAL-ORD-\\d{4}-\\d+/);
        return m ? m[0] : ''; }""")
    if so_name: R["created"].append(("Sales Order", so_name))
    page.keyboard.press("Escape")
    page.wait_for_timeout(1200)
    check("指令单列表含新单", so_name and so_name in page.content(), so_name)

    # ---- 2) 新建采购单 ----
    page.evaluate("location.hash='#/purchase'")
    page.wait_for_selector(".tbl tbody tr", timeout=30000)
    page.click("button.btn-amber")
    page.wait_for_selector("#nf-submit", timeout=30000)
    page.select_option("#nf-item_code", "M-FAB-001")
    page.fill("#nf-qty", "60")
    page.fill("#nf-rate", "20")
    clear_toast(page)
    page.click("#nf-submit")
    toast = wait_toast(page)
    check("新建采购单 toast", "已创建并提交" in toast, toast)
    po_name = page.evaluate("""() => {
        const m = ((document.querySelector('#toast')||{}).textContent||'').match(/PUR-ORD-\\d{4}-\\d+/);
        return m ? m[0] : ''; }""")
    if po_name: R["created"].append(("Purchase Order", po_name))
    page.keyboard.press("Escape")
    page.wait_for_timeout(1000)

    # ---- 3) 新建委外单（PO + SC 两步） ----
    page.evaluate("location.hash='#/subcontract'")
    page.wait_for_selector(".tbl tbody tr", timeout=30000)
    page.click("button.btn-amber")
    page.wait_for_selector("#nf-submit", timeout=30000)
    page.select_option("#nf-svc_item", "SVC-STI")
    page.select_option("#nf-fg_item", "SF-A001")
    page.fill("#nf-qty", "150")
    page.fill("#nf-rate", "12")
    clear_toast(page)
    page.click("#nf-submit")
    toast = wait_toast(page)
    check("新建委外单 toast", "已创建并提交" in toast and "委外采购单" in toast, toast)
    names = page.evaluate("""() => {
        const t = ((document.querySelector('#toast')||{}).textContent||'');
        const sc = (t.match(/SC-ORD-\\d{4}-\\d+/)||[''])[0];
        const po = (t.match(/PUR-ORD-\\d{4}-\\d+/)||[''])[0];
        return {sc, po}; }""")
    if names["sc"]: R["created"].append(("Subcontracting Order", names["sc"]))
    if names["po"]: R["created"].append(("Purchase Order", names["po"]))
    page.keyboard.press("Escape")
    page.wait_for_timeout(1000)

    # ---- 4) 登记付款 ----
    page.evaluate("location.hash='#/finance'")
    page.wait_for_selector("#page .stat-card", timeout=30000)
    page.click("button.btn-amber")
    page.wait_for_selector("#nf-submit", timeout=30000)
    page.select_option("#nf-party", "莆田华盛针车厂")
    page.fill("#nf-paid_amount", "500")
    page.fill("#nf-reference_no", "TEST-UI 付款")
    clear_toast(page)
    page.click("#nf-submit")
    toast = wait_toast(page)
    check("登记付款 toast", "已创建并提交" in toast, toast)
    pay_name = page.evaluate("""() => {
        const m = ((document.querySelector('#toast')||{}).textContent||'').match(/ACC-PAY-\\d{4}-\\d+/);
        return m ? m[0] : ''; }""")
    if pay_name: R["created"].append(("Payment Entry", pay_name))

    check("四类单据全部创建成功", len({d for d, _ in R["created"]}) == 4, str(R["created"]))
    check("无页面 JS 异常", len(R["page_errors"]) == 0, str(R["page_errors"])[:300])
    browser.close()

json.dump(R, open(OUT + "/ui_create_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
fails = [c for c in R["checks"] if not c["ok"]]
print("", flush=True)
print("========== 开单测试: " + str(len(R["checks"]) - len(fails)) + "/" + str(len(R["checks"])) + " PASS ==========", flush=True)
print("创建的单据: " + json.dumps(R["created"], ensure_ascii=False), flush=True)
if fails:
    print("FAILED: " + json.dumps(fails, ensure_ascii=False)[:500], flush=True)
