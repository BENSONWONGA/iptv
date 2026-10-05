# -*- coding: utf-8 -*-
import json, os
from playwright.sync_api import sync_playwright
BASE = "http://127.0.0.1:3333"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
JS = r"""() => {
  const el = document.querySelector('.bal-zero');
  if (!el) return {found: false};
  const probe = document.createElement('div');
  probe.className = 'bal-zero';
  probe.textContent = 'TEST';
  document.body.appendChild(probe);
  const outC = getComputedStyle(probe).color;
  const outS = getComputedStyle(probe).textShadow;
  probe.remove();
  const hits = [];
  const walk = rules => { for (const r of (rules||[])) {
    if (r.cssRules) { walk(r.cssRules); continue; }
    if (!r.selectorText || !r.style || !r.style.color) continue;
    let m = false; try { m = el.matches(r.selectorText); } catch (e) { continue; }
    if (m) hits.push({sel: r.selectorText, color: r.style.color});
  } };
  for (const sh of document.styleSheets) { try { walk(sh.cssRules); } catch (e) {} }
  return {found: true, outOfTableColor: outC, outOfTableShadow: outS,
    inTableColor: getComputedStyle(el).color, inTableShadow: getComputedStyle(el).textShadow,
    matchedRules: hits};
}"""
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=CHROME, args=["--no-sandbox", "--disable-dev-shm-usage"])
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    page.goto(BASE + "#/")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector(".login-view", timeout=15000)
    page.click("#login-btn")
    try:
        page.wait_for_selector(".hero-banner", timeout=90000)
    except Exception:
        pass
    page.wait_for_function("document.querySelector('.hero-banner') && !document.querySelector('#page .skel')", timeout=90000)
    page.evaluate("location.hash = '#/finance'")
    page.wait_for_function("!document.querySelector('#page .skel') && document.querySelector('.bal-zero')", timeout=45000)
    page.wait_for_timeout(400)
    r = page.evaluate(JS)
    print("[BALZERO-EXP] " + json.dumps(r, ensure_ascii=False))
    browser.close()
