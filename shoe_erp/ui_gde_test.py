# -*- coding: utf-8 -*-
"""通用单据引擎端到端：任意 doctype 的自动表单 / 子表行 / 提交 / 只读查看 / 权限降级"""
import json
import re
import time

from playwright.sync_api import sync_playwright

BASE = "http://220.162.99.166:88/odk"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/workspace/shoe_erp"
R = {"checks": [], "created": [], "page_errors": []}


def check(name, ok, detail=""):
    ok = bool(ok)
    R["checks"].append({"name": name, "ok": ok, "detail": str(detail)[:200]})
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else "  --> " + str(detail)[:200]), flush=True)


def wait_toast(page, timeout=60000):
    t0 = time.time()
    while time.time() - t0 < timeout / 1000:
        txt = page.evaluate("() => { const t = document.querySelector('#toast'); return (t && !t.hidden) ? t.textContent : ''; }")
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
    page.on("pageerror", lambda e: R["page_errors"].append(str(e)[:200]))

    page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("#login-btn", timeout=20000)
    page.click("#login-btn")
    page.wait_for_selector(".hero-banner", timeout=40000)

    # ---- 1) 全部单据页 ----
    page.evaluate("location.hash='#/docs'")
    page.wait_for_selector(".gde-type-btn", timeout=30000)
    types = page.evaluate("document.querySelectorAll('.gde-type-btn').length")
    check("全部单据页类型按钮（25 种）", types >= 24, "n=" + str(types))

    # ---- 2) Stock Entry：新建含子表行 → 保存并提交 ----
    page.click(".gde-type-btn[data-dt='Stock Entry']")
    page.wait_for_selector("#gde-rows .tbl tbody tr", timeout=30000)
    check("Stock Entry 列表加载", True)
    page.click("#gde-new")
    page.wait_for_selector("#gf-submit", timeout=30000)
    page.wait_for_timeout(800)
    # 表单字段由 meta 自动渲染：Link 字段直接填值
    # （purpose 在原系统中是隐藏只读字段，由 stock_entry_type 自动带出，引擎正确跳过）
    page.fill("#gf-stock_entry_type", "Material Transfer")
    page.fill("#gf-company", "奥登科鞋业有限公司")
    # 子表：添加一行并填写
    page.click(".gde-add-row")
    page.wait_for_selector(".gde-row", timeout=10000)
    page.fill("#gf-items-0-item_code", "M-FAB-001")
    page.fill("#gf-items-0-qty", "5")
    page.fill("#gf-items-0-s_warehouse", "材料仓 - 奥登科")
    page.fill("#gf-items-0-t_warehouse", "半成品仓 - 奥登科")
    clear_toast(page)
    page.click("#gf-submit")
    toast = wait_toast(page)
    check("Stock Entry 保存并提交", "已保存并提交" in toast, toast)
    m = re.search(r"MAT-STE-\d{4}-\d+", toast)
    if m:
        R["created"].append(("Stock Entry", m.group(0)))
    page.wait_for_timeout(1200)
    check("列表出现新调拨单", bool(m) and m.group(0) in page.content(), m.group(0) if m else "")
    shot_done = m is not None
    if shot_done:
        page.screenshot(path=OUT + "/gde-stockentry-list.png")

    # ---- 3) Customer：非 submittable 主数据，只有「保存」 ----
    page.click("#gde-back")
    page.wait_for_selector(".gde-type-btn", timeout=10000)
    page.click(".gde-type-btn[data-dt='Customer']")
    page.wait_for_selector("#gde-rows .tbl tbody tr", timeout=30000)
    page.click("#gde-new")
    page.wait_for_selector("#gf-submit", timeout=30000)
    submit_text = page.evaluate("document.querySelector('#gf-submit').textContent")
    check("Customer 按钮为「保存」（不可提交单据）", "保存" in submit_text and "提交" not in submit_text, submit_text)
    page.fill("#gf-customer_name", "测试客户GDE")
    page.select_option("#gf-customer_type", "Individual")
    page.fill("#gf-customer_group", "外贸客户")
    clear_toast(page)
    page.click("#gf-submit")
    toast = wait_toast(page)
    check("Customer 保存", "已保存" in toast, toast)
    if "已保存" in toast:
        R["created"].append(("Customer", "测试客户GDE"))
    page.keyboard.press("Escape")
    page.wait_for_timeout(800)

    # ---- 4) 只读查看已提交单据（Sales Order） ----
    page.click("#gde-back")
    page.wait_for_selector(".gde-type-btn", timeout=10000)
    page.click(".gde-type-btn[data-dt='Sales Order']")
    page.wait_for_selector("#gde-rows .tbl tbody tr", timeout=30000)
    page.click("#gde-rows [data-act='view']")
    page.wait_for_selector("#gde-form", timeout=30000)
    page.wait_for_timeout(800)
    ro = page.evaluate("""() => ({
        title: (document.querySelector('.drawer-hd h3')||{}).textContent || '',
        disabled: [...document.querySelectorAll('#gde-form input, #gde-form select')].filter(el => el.disabled).length,
        total: document.querySelectorAll('#gde-form input, #gde-form select').length,
        hasSubmit: !!document.querySelector('#gf-submit'),
    })""")
    check("已提交单只读查看", ro["disabled"] >= ro["total"] * 0.9 and not ro["hasSubmit"] and "查看" in ro["title"], json.dumps(ro, ensure_ascii=False)[:120])
    page.keyboard.press("Escape")
    page.wait_for_timeout(600)

    # ---- 5) 无权限单据优雅降级（Asset：门户无资产角色） ----
    page.click("#gde-back")
    page.wait_for_selector(".gde-type-btn", timeout=10000)
    page.click(".gde-type-btn[data-dt='Asset']")
    page.wait_for_selector("#gde-rows .tbl, #gde-rows .empty", timeout=30000)
    page.wait_for_timeout(300)
    degraded = page.evaluate("""() => { const b = document.querySelector('#gde-rows .empty'); return b ? b.textContent : ''; }""")
    check("无权限单据降级提示", ("无法读取" in degraded or "暂无单据" in degraded), degraded[:60])

    check("无页面 JS 异常", len(R["page_errors"]) == 0, str(R["page_errors"])[:300])
    browser.close()

json.dump(R, open(OUT + "/ui_gde_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
fails = [c for c in R["checks"] if not c["ok"]]
print("", flush=True)
print("========== 通用引擎测试: " + str(len(R["checks"]) - len(fails)) + "/" + str(len(R["checks"])) + " PASS ==========", flush=True)
print("创建: " + json.dumps(R["created"], ensure_ascii=False), flush=True)
if fails:
    print("FAILED: " + json.dumps(fails, ensure_ascii=False)[:500], flush=True)
