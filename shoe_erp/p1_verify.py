# -*- coding: utf-8 -*-
"""批次1功能验证：单据目录搜索(40种) / 列表排序筛选 / 表单打印+复制新建"""
import json
import time

from playwright.sync_api import sync_playwright

BASE = "http://220.162.99.166:88/odk"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/workspace/shoe_erp"
R = {"checks": [], "errors": []}


def check(name, ok, detail=""):
    R["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:150]})
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else "  --> " + str(detail)[:150]), flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True,
                                args=["--proxy-server=http://127.0.0.1:18080", "--no-sandbox", "--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    page.on("pageerror", lambda e: R["errors"].append(str(e)[:150]))
    page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    page.click("#login-btn")
    page.wait_for_selector(".hero-banner", timeout=40000)

    # 1) 目录：40 种单据 + 搜索过滤
    page.evaluate("location.hash='#/docs'")
    page.wait_for_selector("#gde-find", timeout=30000)
    n = page.evaluate("document.querySelectorAll('.gde-type-btn').length")
    check("单据目录 40 种", n >= 40, "n=" + str(n))
    page.fill("#gde-find", "科目")
    page.wait_for_timeout(300)
    hits = page.evaluate("[...document.querySelectorAll('.gde-type-btn')].filter(b => b.style.display !== 'none').length")
    check("目录搜索「科目」命中会计科目", hits == 1, "hits=" + str(hits))
    page.fill("#gde-find", "")
    page.wait_for_timeout(200)

    # 2) Stock Entry 列表：排序 + 筛选
    page.click(".gde-type-btn[data-dt='Stock Entry']")
    page.wait_for_selector("#gde-rows .tbl tbody tr", timeout=30000)
    has_ctl = page.evaluate("!!document.querySelector('#gde-sort') && !!document.querySelector('#gde-filter-field') && !!document.querySelector('#gde-filter-apply')")
    check("列表工具栏（排序+筛选）", has_ctl)
    page.select_option("#gde-sort", "name asc")
    page.wait_for_timeout(1500)
    first = page.evaluate("document.querySelector('#gde-rows .tbl tbody tr td').textContent")
    check("排序=编号升序后首行为 00001", "00001" in str(first), first)
    page.select_option("#gde-filter-field", "stock_entry_type")
    page.select_option("#gde-filter-op", "like")
    page.fill("#gde-filter-val", "Material Transfer")
    page.click("#gde-filter-apply")
    page.wait_for_timeout(1500)
    rows = page.evaluate("document.querySelectorAll('#gde-rows .tbl tbody tr').length")
    types = page.evaluate("[...document.querySelectorAll('#gde-rows .tbl tbody tr td:nth-child(2)')].map(t => t.textContent)")
    check("筛选「物料调拨」后行数一致", rows > 0 and all("调拨" in t for t in types), json.dumps(types[:3], ensure_ascii=False))
    page.click("#gde-filter-clear")
    page.wait_for_timeout(1200)
    page.screenshot(path=OUT + "/p1-list-toolbar.png")

    # 3) 表单：打印按钮 + 复制新建
    page.click("#gde-rows [data-act='view']")
    page.wait_for_selector("#gde-form", timeout=30000)
    page.wait_for_timeout(600)
    acts = page.evaluate("""() => ({
        print: !!document.querySelector('#gf-print'),
        dup: !!document.querySelector('#gf-dup'),
        title: (document.querySelector('.drawer-hd h3')||{}).textContent || '',
    })""")
    check("已提交单有「打印PDF / 复制新建」", acts["print"] and acts["dup"] and "查看" in acts["title"], json.dumps(acts, ensure_ascii=False)[:100])
    page.click("#gf-dup")
    page.wait_for_timeout(1200)
    dup = page.evaluate("""() => ({
        title: (document.querySelector('.drawer-hd h3')||{}).textContent || '',
        enabled: [...document.querySelectorAll('#gde-form input, #gde-form select')].filter(el => !el.disabled).length,
        total: document.querySelectorAll('#gde-form input, #gde-form select').length,
        firstItem: (document.querySelector('#gf-items-0-item_code')||{}).value || '',
    })""")
    check("复制新建打开可编辑预填表单", "复制新建" in dup["title"] and dup["enabled"] > dup["total"] * 0.9 and dup["firstItem"].startswith("M-"), json.dumps(dup, ensure_ascii=False)[:150])
    page.screenshot(path=OUT + "/p1-dup-drawer.png")
    check("无页面 JS 异常", len(R["errors"]) == 0, str(R["errors"])[:200])
    browser.close()

fails = [c for c in R["checks"] if not c["ok"]]
print("\n========== 批次1验证: " + str(len(R["checks"]) - len(fails)) + "/" + str(len(R["checks"])) + " PASS ==========")
json.dump(R, open(OUT + "/p1_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if fails:
    print("FAILED: " + json.dumps(fails, ensure_ascii=False)[:300])
