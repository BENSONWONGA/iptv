# -*- coding: utf-8 -*-
"""v3.1 截图像素级核验：DOM rect + PIL 采样，确认视觉渲染与结构一致"""
import json, os
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3333"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/workspace/shoe_erp"
VW, VH = 1440, 900

RECT_JS = r"""() => {
  const R = (sel) => { const el = document.querySelector(sel); if (!el) return null;
    const r = el.getBoundingClientRect(); return {x:+r.x.toFixed(1), y:+r.y.toFixed(1), w:+r.width.toFixed(1), h:+r.height.toFixed(1)}; };
  return {
    loginLeft: R('.login-left'), loginRight: R('.login-right'), lrCard: R('.lr-card'),
    hero: R('.hero-banner'), hbL: R('.hb-l'),
    chips: [...document.querySelectorAll('.hb-chip')].map(c => { const r = c.getBoundingClientRect();
      return {x:+r.x.toFixed(1), y:+r.y.toFixed(1), w:+r.width.toFixed(1), h:+r.height.toFixed(1)}; }),
    statIcs: [...document.querySelectorAll('.stat-card .stat-ic')].map(c => { const r = c.getBoundingClientRect();
      return {cls: [...c.classList].filter(x=>x!=='stat-ic').join(','), x:+r.x.toFixed(1), y:+r.y.toFixed(1), w:+r.width.toFixed(1), h:+r.height.toFixed(1)}; }),
    pillOk: R('.fc-sum .pill.ok'), fcNum: R('.fc-num'),
    phIc: R('.page-hd .ph-ic'), statIcSub: [...document.querySelectorAll('.stat-card .stat-ic')].map(c => { const r = c.getBoundingClientRect();
      return {cls: [...c.classList].filter(x=>x!=='stat-ic').join(','), x:+r.x.toFixed(1), y:+r.y.toFixed(1), w:+r.width.toFixed(1), h:+r.height.toFixed(1)}; })
  };
}"""


def main():
    res = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=CHROME, args=["--no-first-run", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": VW, "height": VH}, locale="zh-CN")
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})

        # 登录页
        page.goto(BASE + "/#/")
        page.wait_for_selector(".login-view", timeout=15000)
        page.wait_for_timeout(500)
        res["login"] = page.evaluate(RECT_JS)
        page.screenshot(path=os.path.join(OUT, "v31-px-login.png"))

        # 登录 -> 工作台
        page.click("#login-btn")
        page.wait_for_function("document.querySelector('.hero-banner') && !document.querySelector('#page .skel')", timeout=30000)
        page.wait_for_timeout(500)
        res["dashboard"] = page.evaluate(RECT_JS)
        page.screenshot(path=os.path.join(OUT, "v31-px-dashboard.png"), full_page=True)

        # 应付对账页（统一页面头 + 统计卡）
        page.click('.tnav a[data-page="finance"]')
        page.wait_for_function("() => { const a=document.querySelector('.tnav a.active'); return a && a.dataset.page==='finance' && document.querySelector('#page .page-hd') && !document.querySelector('#page .skel'); }", timeout=40000)
        page.wait_for_timeout(400)
        res["finance"] = page.evaluate(RECT_JS)
        page.screenshot(path=os.path.join(OUT, "v31-px-finance.png"), full_page=True)
        browser.close()

    # ---------------- PIL 像素核验 ----------------
    from PIL import Image
    checks = []
    def C(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": str(detail)[:200]})
        print(("[PX-PASS] " if ok else "[PX-FAIL] ") + name + ("" if ok else " --> " + str(detail)[:150]), flush=True)

    def px(img, x, y):
        return img.getpixel((int(x), int(y)))[:3]

    def is_blue(c):  return c[2] >= 90 and c[2] > c[0] + 15 and c[1] < c[2] + 45
    def is_whiteish(c): return all(v >= 235 for v in c)
    def is_cyan(c): return c[2] >= 120 and c[1] >= 120 and c[0] < c[1] - 20
    def is_amber(c): return c[0] >= 180 and c[0] > c[2] + 40 and c[1] > 100
    def is_green(c): return c[1] >= 100 and c[1] > c[0] + 20 and c[1] > c[2] + 10

    # 登录页
    img = Image.open(os.path.join(OUT, "v31-px-login.png")).convert("RGB")
    L = res["login"]["loginLeft"]; Rt = res["login"]["loginRight"]
    c1 = px(img, L["x"] + L["w"] / 2, VH / 2)
    C("登录页左半为品牌蓝渐变", is_blue(c1), f"px={c1}")
    c2 = px(img, 1435, 10)
    C("登录页右半为白色表单区", is_whiteish(c2), f"px={c2}")
    card = res["login"]["lrCard"]
    c3 = px(img, card["x"] + card["w"] / 2, card["y"] - 30 if card["y"] > 60 else card["y"] + 5)
    # 表单卡上缘之外的右侧区域应为白
    c3b = px(img, Rt["x"] + 30, Rt["y"] + 40)
    C("登录页右侧区域留白为白（表单居中非贴左）", is_whiteish(c3b), f"px={c3b} rightX={Rt['x']}")

    # 工作台
    img = Image.open(os.path.join(OUT, "v31-px-dashboard.png")).convert("RGB")
    H = res["dashboard"]["hero"]
    hb = px(img, H["x"] + 40, H["y"] + H["h"] / 2)
    C("工作台横幅为品牌蓝", is_blue(hb), f"px={hb} rect={H}")
    chip_px = [px(img, c["x"] + c["w"] / 2, c["y"] + 8) for c in res["dashboard"]["chips"]]
    lighter = all(c[0] > hb[0] + 12 for c in chip_px)  # 半透明白胶囊叠在蓝底上更亮
    C("横幅右侧胶囊为半透明白（比横幅底更亮）", len(chip_px) == 3 and lighter, f"chips={chip_px} vs banner={hb}")
    exp = {"blue": is_blue, "cyan": is_cyan, "amber": is_amber, "green": is_green}
    def block_color(img, s):
        # 图标块中央有白色 SVG 图形，采四角+中心多点，任一命中渐变底色即可
        pts = [(s["x"] + s["w"] - 6, s["y"] + 6), (s["x"] + 6, s["y"] + 6), (s["x"] + 6, s["y"] + s["h"] - 6),
               (s["x"] + s["w"] - 6, s["y"] + s["h"] - 6), (s["x"] + s["w"] / 2, s["y"] + s["h"] / 2)]
        return [px(img, x, y) for x, y in pts]
    for s in res["dashboard"]["statIcs"]:
        cols = block_color(img, s)
        C(f"统计卡图标块 {s['cls']} 渐变色正确", any(exp[s["cls"]](c) for c in cols), f"pts={cols}")
    P = res["dashboard"]["pillOk"]
    pill_pts = [px(img, P["x"] + 6, P["y"] + P["h"] / 2), px(img, P["x"] + P["w"] - 6, P["y"] + P["h"] / 2), px(img, P["x"] + P["w"] / 2, P["y"] + 3)]
    light_green = any(all(v > 180 for v in c) and c[1] >= c[0] for c in pill_pts)
    C("「已全部完成」pill 为浅绿底", light_green, f"pts={pill_pts}")

    # 应付对账页
    img = Image.open(os.path.join(OUT, "v31-px-finance.png")).convert("RGB")
    PH = res["finance"]["phIc"]
    if PH:
        cols = block_color(img, PH)
        C("应付对账页头 44px 图标块为品牌蓝渐变", any(is_blue(c) for c in cols), f"pts={cols} rect={PH}")
    for s in res["finance"]["statIcSub"]:
        cols = block_color(img, s)
        C(f"应付对账统计卡图标块 {s['cls']} 色正确", any(exp[s["cls"]](c) for c in cols), f"pts={cols}")

    n_pass = sum(1 for c in checks if c["ok"])
    print(f"\n=== 像素核验: {n_pass} PASS / {len(checks) - n_pass} FAIL ===", flush=True)
    with open(os.path.join(OUT, "v31_px_result.json"), "w", encoding="utf-8") as f:
        json.dump({"rects": res, "checks": checks}, f, ensure_ascii=False, indent=1)
    # 清理临时截图
    for t in ("v31-px-login.png", "v31-px-dashboard.png", "v31-px-finance.png"):
        try: os.remove(os.path.join(OUT, t))
        except OSError: pass


if __name__ == "__main__":
    main()
