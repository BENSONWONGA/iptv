# -*- coding: utf-8 -*-
"""物料管理端到端测试：新建物料 → 新建 BOM（动态组件行）→ MRP 采购申请（计算净需求→提交）"""
import json
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

    # ---- 1) 物料管理页加载 ----
    page.evaluate("location.hash='#/material'")
    page.wait_for_selector("#page .tbl tbody tr", timeout=30000)
    page.wait_for_timeout(1200)
    mat = page.evaluate("""() => ({
        stats: document.querySelectorAll('#page .stat-card').length,
        bomRows: [...document.querySelectorAll('#page .card')][1] ? document.querySelectorAll('#page .card:nth-of-type(3) .tbl tbody tr').length : 0,
        pills: [...document.querySelectorAll('.page-hd .pill')].map(p => p.textContent.trim()),
    })""")
    check("物料管理页 3 张统计卡", mat["stats"] == 3, str(mat))
    check("导航含「物料管理」", "物料管理" in page.content())

    # ---- 2) 新建物料 ----
    page.click("button.btn-amber:nth-of-type(1)")  # ＋ 新建物料
    page.wait_for_selector("#nf-submit", timeout=20000)
    page.wait_for_selector("#nf-item_code", state="attached", timeout=10000)
    page.fill("#nf-item_code", "TEST-UI-MAT-01")
    page.fill("#nf-item_name", "测试网布(白色)")
    page.select_option("#nf-item_group", "辅料")
    page.select_option("#nf-stock_uom", "Nos")
    page.fill("#nf-barcode", "6901234500099")
    clear_toast(page)
    page.click("#nf-submit")
    toast = wait_toast(page)
    check("新建物料 toast", "TEST-UI-MAT-01" in toast and "已创建" in toast, toast)
    if "TEST-UI-MAT-01" in toast:
        R["created"].append(("Item", "TEST-UI-MAT-01"))
    page.wait_for_timeout(1500)
    check("物料档案表出现新物料", "TEST-UI-MAT-01" in page.content())

    # ---- 3) 新建 BOM（给 FG-A001-42-BK，含两行动态组件） ----
    page.click("button.btn-amber:nth-of-type(2)")  # ＋ 新建 BOM
    page.wait_for_selector("#bom-rows .bom-row", timeout=20000)
    page.wait_for_selector("#nf-item option", state="attached", timeout=15000)
    page.select_option("#nf-item", "FG-A001-42-BK")
    page.fill("#nf-quantity", "1")
    page.select_option(".bom-row:nth-child(1) .br-item", "M-FAB-001")
    page.fill(".bom-row:nth-child(1) .br-qty", "2")
    page.select_option(".bom-row:nth-child(2) .br-item", "M-ACC-001")
    page.fill(".bom-row:nth-child(2) .br-qty", "4")
    clear_toast(page)
    page.click("#nf-submit")
    toast = wait_toast(page)
    check("新建 BOM toast", "BOM" in toast and "已创建并提交" in toast, toast)
    import re
    m = re.search(r"BOM-FG-[A-Z0-9-]+-\d+", toast)
    if m:
        R["created"].append(("BOM", m.group(0)))
    page.wait_for_timeout(1500)

    # ---- 4) MRP 采购申请（选指令单 → 计算净需求 → 提交） ----
    page.click("button.btn-amber:nth-of-type(3)")  # ⚙ MRP
    page.wait_for_selector("#nf-so option", state="attached", timeout=15000)
    page.select_option("#nf-so", "SAL-ORD-2026-00002")
    clear_toast(page)
    page.click("#mrp-run")
    try:
        page.wait_for_selector("#mrp-result .tbl tbody tr", timeout=30000)
        page.wait_for_timeout(500)
        mrp_rows = page.evaluate("document.querySelectorAll('#mrp-result .tbl tbody tr').length")
        check("MRP 净需求计算结果有行", mrp_rows > 0, "rows=" + str(mrp_rows))
    except Exception as e:
        check("MRP 净需求计算结果有行", False, str(e)[:150])
    clear_toast(page)
    page.click("#nf-submit")
    toast = wait_toast(page)
    check("MRP 采购申请 toast", "采购申请" in toast and "已创建并提交" in toast, toast)
    m = re.search(r"MAT-MR-\d{4}-\d+", toast)
    if m:
        R["created"].append(("Material Request", m.group(0)))
    page.wait_for_timeout(1500)
    check("采购申请列表含新单", bool(m) and m.group(0) in page.content(), m.group(0) if m else "")

    check("无页面 JS 异常", len(R["page_errors"]) == 0, str(R["page_errors"])[:300])
    browser.close()

json.dump(R, open(OUT + "/ui_material_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
fails = [c for c in R["checks"] if not c["ok"]]
print("", flush=True)
print("========== 物料/BOM/MRP 测试: " + str(len(R["checks"]) - len(fails)) + "/" + str(len(R["checks"])) + " PASS ==========", flush=True)
print("创建: " + json.dumps(R["created"], ensure_ascii=False), flush=True)
if fails:
    print("FAILED: " + json.dumps(fails, ensure_ascii=False)[:500], flush=True)
