# -*- coding: utf-8 -*-
"""237单 走流程结果截图：指令单中心 / 全链路抽屉 / 物料管理(MRP+采购申请)"""
from playwright.sync_api import sync_playwright

BASE = "http://220.162.99.166:88/odk"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/workspace"

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True,
                                args=["--proxy-server=http://127.0.0.1:18080", "--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
    page.goto(BASE, wait_until="domcontentloaded", timeout=60000)
    page.click("#login-btn")
    page.wait_for_selector(".hero-banner", timeout=40000)

    # 1) 指令单中心：237单 在列表
    page.evaluate("location.hash='#/orders'")
    page.wait_for_selector("#page .tbl tbody tr", timeout=30000)
    page.wait_for_timeout(800)
    hit = "237单" in page.content()
    print("指令单中心含 237单:", hit)
    page.screenshot(path=f"{OUT}/237-orders.png")

    # 2) 237单 全链路抽屉
    page.evaluate("openChainDrawer('237单')")
    page.wait_for_timeout(2500)
    page.screenshot(path=f"{OUT}/237-chain.png")

    # 3) 物料管理：BOM + MRP 采购申请
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    page.evaluate("location.hash='#/material'")
    page.wait_for_selector("#page .card", timeout=30000)
    page.wait_for_timeout(800)
    page.screenshot(path=f"{OUT}/237-material.png", full_page=True)
    browser.close()
print("截图完成")
