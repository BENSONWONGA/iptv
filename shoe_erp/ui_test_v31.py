# -*- coding: utf-8 -*-
"""
v3.1 UI 视觉升级验收 —— 本地 Playwright + Chrome 直连 http://127.0.0.1:3333（禁用缓存）
验证: 登录页分屏 46/54、工作台横幅/统计卡/流程卡、8 个子页统一页面头、回归(console/pageerror/溢出/扫码)
截图: v31-login-fixed.png v31-dashboard.png v31-orders.png v31-purchase.png v31-subcontract.png
      v31-production.png v31-warehouse.png v31-scan.png v31-finance.png v31-flow.png
输出: v31_result.json / v31_test.log
"""
import json, os, re, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3333"
DEMO_TOKEN = "77455c7d4b3a8fe:f36c1a4b10e8b5e"
CHROME = "/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome"
OUT = "/workspace/shoe_erp"
BARCODE = "6901234500011"
VW, VH = 1440, 900

R = {"meta": {}, "login": {}, "dashboard": {}, "pages": {}, "scan": {}, "regression": {},
     "checks": [], "console": [], "pageerrors": [], "net_err": []}


def check(phase, name, ok, detail=""):
    ok = bool(ok)
    R["checks"].append({"phase": phase, "name": name, "ok": ok, "detail": str(detail)[:400]})
    print(("  [PASS] " if ok else "  [FAIL] ") + name + ("" if ok else "   --> " + str(detail)[:220]), flush=True)


def shot(page, name):
    path = os.path.join(OUT, name)
    page.screenshot(path=path, full_page=True)
    print("  [SHOT] " + path, flush=True)
    return path


# ---------- JS 探针 ----------
LOGIN_JS = r"""() => {
  const cs = (sel, prop) => { const el = document.querySelector(sel); return el ? getComputedStyle(el)[prop] : null; };
  const L = document.querySelector('.login-left'); const Rt = document.querySelector('.login-right');
  const C = document.querySelector('.lr-card');
  if (!L || !Rt || !C) return {missing: true};
  const l = L.getBoundingClientRect(), r = Rt.getBoundingClientRect(), c = C.getBoundingClientRect();
  return {
    vw: innerWidth, gridCols: cs('.login-view','gridTemplateColumns'),
    leftW: +l.width.toFixed(1), leftRatio: +(l.width/innerWidth).toFixed(4),
    rightW: +r.width.toFixed(1), rightRatio: +(r.width/innerWidth).toFixed(4),
    rightX: +r.x.toFixed(1),
    cardW: +c.width.toFixed(1), cardX: +c.x.toFixed(1),
    cardCx: +(c.x + c.width/2).toFixed(1), rightCx: +(r.x + r.width/2).toFixed(1),
    cardOffset: +(c.x + c.width/2 - (r.x + r.width/2)).toFixed(1),
    leftBg: cs('.login-left','backgroundImage'),
    baseValue: (document.querySelector('#login-base')||{}).value || '',
    tokenValue: (document.querySelector('#login-token')||{}).value || '',
    btnText: ((document.querySelector('#login-btn')||{}).textContent||'').trim(),
    errText: ((document.querySelector('#login-err')||{}).textContent||'').trim(),
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

DASH_JS = r"""() => {
  const cs = (sel, prop, ps) => { const el = document.querySelector(sel); return el ? getComputedStyle(el, ps||null)[prop] : null; };
  const hero = document.querySelector('.hero-banner');
  const heroAfter = hero ? getComputedStyle(hero, '::after') : null;
  const chips = [...document.querySelectorAll('.hb-chip')].map(c => c.textContent.trim().replace(/\s+/g,' '));
  const statCards = [...document.querySelectorAll('.stat-card')].map(c => {
    const ic = c.querySelector('.stat-ic');
    const ir = ic ? ic.getBoundingClientRect() : null;
    return { icClass: ic ? [...ic.classList].filter(x=>x!=='stat-ic').join(',') : null,
             icW: ir ? +ir.width.toFixed(1) : null, icH: ir ? +ir.height.toFixed(1) : null,
             icRadius: ic ? getComputedStyle(ic).borderRadius : null,
             icBg: ic ? getComputedStyle(ic).backgroundImage.slice(0,80) : null,
             label: (c.querySelector('.stat-label')||{}).textContent || '',
             value: (c.querySelector('.stat-value')||{}).textContent || '',
             valueSize: c.querySelector('.stat-value') ? getComputedStyle(c.querySelector('.stat-value')).fontSize : null,
             foot: (c.querySelector('.stat-foot')||{}).textContent || '' };
  });
  const fcNum = document.querySelector('.fc-num');
  const dot = document.querySelector('.fb-dot');
  const hr = hero ? hero.getBoundingClientRect() : null;
  const todoHd = [...document.querySelectorAll('.card-hd')].map(h => h.textContent.trim().replace(/\s+/g,' ').slice(0,50));
  return {
    heroExists: !!hero,
    heroRadius: hero ? getComputedStyle(hero).borderRadius : null,
    heroBg: hero ? getComputedStyle(hero).backgroundImage.slice(0,110) : null,
    heroColor: hero ? getComputedStyle(hero).color : null,
    heroW: hr ? +hr.width.toFixed(1) : null,
    heroAfterW: heroAfter ? heroAfter.width : null, heroAfterH: heroAfter ? heroAfter.height : null,
    heroAfterRadius: heroAfter ? heroAfter.borderRadius : null,
    heroAfterBg: heroAfter ? (heroAfter.background || heroAfter.backgroundImage || '').slice(0,60) : null,
    heroH2: (document.querySelector('.hb-l h2')||{}).textContent || '',
    heroH2Color: cs('.hb-l h2','color'), heroH2Size: cs('.hb-l h2','fontSize'),
    heroP: (document.querySelector('.hb-l p')||{}).textContent || '',
    chipCount: chips.length, chips,
    chipBg: cs('.hb-chip','backgroundColor'), chipBorder: cs('.hb-chip','borderTopColor'), chipRadius: cs('.hb-chip','borderRadius'),
    statCount: statCards.length, statCards,
    fcNum: fcNum ? fcNum.textContent.trim().replace(/\s+/g,' ') : null,
    fcNumSize: fcNum ? getComputedStyle(fcNum).fontSize : null,
    fcNumIColor: (fcNum && fcNum.querySelector('i')) ? getComputedStyle(fcNum.querySelector('i')).color : null,
    pillOk: (document.querySelector('.fc-sum .pill.ok')||{}).textContent || '',
    pillOkBg: cs('.fc-sum .pill.ok','backgroundColor'), pillOkColor: cs('.fc-sum .pill.ok','color'),
    flowBtn: (document.querySelector('.fc-sum .btn-sm.amber')||{}).textContent || '',
    dotW: dot ? +dot.getBoundingClientRect().width.toFixed(1) : null,
    dotH: dot ? +dot.getBoundingClientRect().height.toFixed(1) : null,
    todoHds: todoHd,
    todoPill: (document.querySelector('.card-hd .pill')||{}).textContent || '',
    whBtn: (document.querySelector('.card-hd .btn-sm.ghost')||{}).textContent || '',
    skelInPage: !!document.querySelector('#page .skel'),
    loadFail: document.body.textContent.includes('加载失败'),
    overflowX: document.documentElement.scrollWidth - innerWidth
  };
}"""

PAGE_JS = r"""() => {
  const hd = document.querySelector('.page-hd');
  if (!hd) return {exists: false, overflowX: document.documentElement.scrollWidth - innerWidth,
                   loadFail: document.body.textContent.includes('加载失败'), statCount: 0, statCards: [],
                   rightHasPillOrBtn: false, icW: null, icH: null, icBg: null, icRadius: null,
                   title: '', titleSize: null, sub: '', subColor: null, subSize: null,
                   rightText: '', skelInPage: !!document.querySelector('#page .skel'), activeNav: ''};
  const ic = hd.querySelector('.ph-ic');
  const h2 = hd.querySelector('h2');
  const sm = h2 ? h2.querySelector('small') : null;
  const right = hd.querySelector('.ph-r');
  const statCards = [...document.querySelectorAll('.stat-card')].map(c => {
    const s = c.querySelector('.stat-ic');
    const sr = s ? s.getBoundingClientRect() : null;
    return { hasIc: !!s, icW: sr ? +sr.width.toFixed(1) : null, icH: sr ? +sr.height.toFixed(1) : null,
             icBg: s ? getComputedStyle(s).backgroundImage.slice(0,70) : null,
             display: getComputedStyle(c).display, gap: getComputedStyle(c).gap,
             label: (c.querySelector('.stat-label, .st-label, b')||{}).textContent || '' };
  });
  const icr = ic ? ic.getBoundingClientRect() : null;
  return {
    exists: true,
    icW: icr ? +icr.width.toFixed(1) : null, icH: icr ? +icr.height.toFixed(1) : null,
    icRadius: ic ? getComputedStyle(ic).borderRadius : null,
    icBg: ic ? getComputedStyle(ic).backgroundImage.slice(0,90) : null,
    title: h2 ? h2.childNodes[0].textContent.trim() : '',
    titleSize: h2 ? getComputedStyle(h2).fontSize : null,
    sub: sm ? sm.textContent.trim() : '',
    subColor: sm ? getComputedStyle(sm).color : null, subSize: sm ? getComputedStyle(sm).fontSize : null,
    rightHasPillOrBtn: right ? !!(right.querySelector('.pill, button')) : false,
    rightText: right ? right.textContent.trim().replace(/\s+/g,' ').slice(0,60) : '',
    statCount: statCards.length, statCards,
    skelInPage: !!document.querySelector('#page .skel'),
    loadFail: document.body.textContent.includes('加载失败'),
    overflowX: document.documentElement.scrollWidth - innerWidth,
    activeNav: (document.querySelector('.tnav a.active')||{dataset:{}}).dataset.page || ''
  };
}"""

SCAN_JS = r"""() => ({
  state: (document.querySelector('#scan-state')||{}).textContent || '',
  count: (document.querySelector('#scan-count')||{}).textContent || '',
  detailHasForm: !!document.querySelector('#scan-detail form, #scan-detail select, #scan-detail .card-bd:not(.empty)'),
  detailText: (document.querySelector('#scan-detail')||{}).textContent.trim().replace(/\s+/g,' ').slice(0,120),
  inputValue: (document.querySelector('#scan-input')||{}).value || ''
})"""

NAV_PAGES = [
    ("orders", "指令单中心"), ("purchase", "采购管理"), ("subcontract", "委外加工"),
    ("production", "生产制造"), ("warehouse", "仓库管理"), ("scan", "扫码出入库"),
    ("finance", "应付对账"), ("flow", "流程链路图"),
]

GREEN_RE = re.compile(r"rgb\(\s*22\s*,\s*163\s*,\s*74\)")


def main():
    t0 = time.time()
    print("=== v3.1 UI 视觉升级验收（Playwright + Chrome 直连，禁用缓存） ===", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True, executable_path=CHROME if os.path.exists(CHROME) else None,
            args=["--no-first-run", "--no-default-browser-check", "--disable-dev-shm-usage"])
        ctx = browser.new_context(viewport={"width": VW, "height": VH}, locale="zh-CN")
        page = ctx.new_page()

        # 禁用缓存（CDP）
        cdp = ctx.new_cdp_session(page)
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        print("[i] CDP Network.setCacheDisabled 已启用（缓存禁用）", flush=True)

        page.on("console", lambda m: R["console"].append({"type": m.type, "text": m.text[:200]}) if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: R["pageerrors"].append(str(e)[:300]))
        page.on("requestfailed", lambda r: R["net_err"].append({"url": r.url[:160], "fail": str(r.failure)[:120]}))

        # ---------------- 1. 登录页 ----------------
        print("\n--- [1] 登录页分屏修复 ---", flush=True)
        page.goto(BASE + "/#/")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector(".login-view", timeout=15000)
        page.wait_for_timeout(600)
        lg = page.evaluate(LOGIN_JS)
        R["login"] = lg
        check("login", "左侧品牌区宽度 ≈46% (662px @1440)", abs(lg["leftRatio"] - 0.46) < 0.011,
              f"leftW={lg['leftW']}px ratio={lg['leftRatio']} gridCols={lg['gridCols']}")
        check("login", "右侧表单区 54%", abs(lg["rightRatio"] - 0.54) < 0.011, f"rightW={lg['rightW']}px ratio={lg['rightRatio']}")
        check("login", "表单在右侧区域内居中（无 400px 右留白）", abs(lg["cardOffset"]) < 15,
              f"cardCx={lg['cardCx']} rightCx={lg['rightCx']} offset={lg['cardOffset']}px cardW={lg['cardW']}")
        check("login", "左侧品牌蓝渐变背景", "linear-gradient" in (lg["leftBg"] or ""), lg["leftBg"][:90])
        check("login", "演示令牌已自动预填", lg["tokenValue"] == DEMO_TOKEN, lg["tokenValue"])
        check("login", "登录页无横向溢出", lg["overflowX"] <= 0, f"overflowX={lg['overflowX']}")
        shot(page, "v31-login-fixed.png")

        # ---------------- 2. 登录 -> 工作台 ----------------
        print("\n--- [2] 登录 -> 工作台 ---", flush=True)
        page.click("#login-btn")
        try:
            page.wait_for_selector(".hero-banner", timeout=30000)
        except Exception:
            pass
        page.wait_for_function("document.querySelector('.hero-banner') && !document.querySelector('#page .skel')", timeout=30000)
        page.wait_for_timeout(500)
        d = page.evaluate(DASH_JS)
        R["dashboard"] = d
        check("dash", "欢迎横幅存在且圆角16px", d["heroExists"] and d["heroRadius"] == "16px", f"radius={d['heroRadius']} w={d['heroW']}")
        check("dash", "横幅为品牌蓝渐变", "linear-gradient" in (d["heroBg"] or ""), (d["heroBg"] or "")[:100])
        check("dash", "横幅白字（h2 + 副标题）", d["heroColor"] == "rgb(255, 255, 255)" and bool(re.match(r"^(早上|中午|下午|晚上)好，系统管理员$", d["heroH2"])),
              f"h2={d['heroH2']!r} color={d['heroH2Color']} p={d['heroP'][:40]!r}")
        check("dash", "日期副标题含 2026", "2026" in d["heroP"], d["heroP"][:60])
        check("dash", "右侧 3 个半透明白胶囊数字卡", d["chipCount"] == 3 and all(k in "".join(d["chips"]) for k in ["累计接单", "成品库存", "未结货款"]),
              f"chips={d['chips']} bg={d['chipBg']} border={d['chipBorder']}")
        check("dash", "胶囊为半透明白背景", "rgba(255, 255, 255" in (d["chipBg"] or ""), f"bg={d['chipBg']}")
        check("dash", "横幅右上角大圆形淡光装饰(::after 300px 圆)",
              d["heroAfterW"] == "300px" and d["heroAfterH"] == "300px" and d["heroAfterRadius"] == "50%",
              f"after={d['heroAfterW']}/{d['heroAfterH']} r={d['heroAfterRadius']} bg={d['heroAfterBg']}")
        check("dash", "4 张横向统计卡", d["statCount"] == 4, f"count={d['statCount']}")
        ok_ic = all(c["icW"] == 46 and c["icH"] == 46 for c in d["statCards"])
        ok_cls = [c["icClass"] for c in d["statCards"]] == ["blue", "cyan", "amber", "green"]
        ok_grad = all("linear-gradient" in (c["icBg"] or "") for c in d["statCards"])
        check("dash", "统计卡图标块 46px 且蓝/青/琥珀/绿渐变", ok_ic and ok_cls and ok_grad,
              f"ic={[ (c['icClass'], c['icW']) for c in d['statCards'] ]}")
        ok_body = all(c["label"] and c["value"] and c["foot"] for c in d["statCards"])
        check("dash", "统计卡含 标签+大数字+小字说明", ok_body, f"cards={[(c['label'], c['value'], c['foot']) for c in d['statCards']]}")
        check("dash", "流程卡头部 14 / 14 大数字（绿色14）", d["fcNum"] == "14 / 14" and GREEN_RE.match(d["fcNumIColor"] or ""),
              f"fcNum={d['fcNum']!r} iColor={d['fcNumIColor']} size={d['fcNumSize']}")
        _m = re.match(r"rgb\((\d+), (\d+), (\d+)\)", d["pillOkBg"] or "")
        pill_green = d["pillOkColor"] == "rgb(22, 163, 74)" and bool(_m) and min(map(int, _m.groups())) > 180 and int(_m.group(2)) >= int(_m.group(1))
        check("dash", "「已全部完成」绿 pill + 「查看完整链路」按钮",
              d["pillOk"] == "已全部完成" and d["flowBtn"] == "查看完整链路" and pill_green,
              f"pill={d['pillOk']!r} btn={d['flowBtn']!r} pillBg={d['pillOkBg']} pillColor={d['pillOkColor']}")
        check("dash", "步骤圆点 32px", d["dotW"] == 32 and d["dotH"] == 32, f"dot={d['dotW']}x{d['dotH']}")
        check("dash", "待办卡头部 pill 徽章", bool(d["todoPill"]), f"pill={d['todoPill']!r} hds={d['todoHds']}")
        check("dash", "库存卡头部「仓库明细」按钮", d["whBtn"] == "仓库明细", f"btn={d['whBtn']!r}")
        check("dash", "工作台无骨架卡死/加载失败", not d["skelInPage"] and not d["loadFail"], f"skel={d['skelInPage']} fail={d['loadFail']}")
        check("dash", "工作台无横向溢出", d["overflowX"] <= 0, f"overflowX={d['overflowX']}")
        shot(page, "v31-dashboard.png")

        # ---------------- 3. 其余页面统一页面头 ----------------
        print("\n--- [3] 8 个子页统一页面头 ---", flush=True)
        R["pages"] = {}
        for key, cname in NAV_PAGES:
            page.click(f'.tnav a[data-page="{key}"]')
            try:
                page.wait_for_function(
                    "([k]) => { const a = document.querySelector('.tnav a.active');"
                    "return !!a && a.dataset.page === k"
                    " && !!document.querySelector('#page .page-hd') && !document.querySelector('#page .skel'); }",
                    arg=[key], timeout=40000)
            except Exception as e:
                check("pages", f"{cname} 页面渲染完成（无骨架卡死）", False, f"等待 .page-hd 超时: {e}")
                shot(page, f"v31-{key}.png")
                R["pages"][key] = {"timeout": True}
                continue
            page.wait_for_timeout(400)
            d = page.evaluate(PAGE_JS)
            R["pages"][key] = d
            check("pages", f"{cname} 页面渲染完成（无骨架卡死/加载失败）", not d.get("loadFail") and not d.get("skelInPage"), f"loadFail={d.get('loadFail')} skel={d.get('skelInPage')}")
            check("pages", f"{cname} 页面头存在且标题/导航激活正确", d.get("exists") and d.get("title") == cname and d.get("activeNav") == key,
                  f"title={d.get('title')!r} activeNav={d.get('activeNav')!r}")
            check("pages", f"{cname} 44px 品牌蓝渐变图标块",
                  d.get("exists") and d.get("icW") == 44 and d.get("icH") == 44 and "linear-gradient" in (d.get("icBg") or ""),
                  f"ic={d.get('icW')}x{d.get('icH')} radius={d.get('icRadius')} bg={d.get('icBg')}")
            _sub_ok = d.get("exists") and d.get("title") and d.get("sub") and (d.get("subColor") or "").startswith("rgb(")
            check("pages", f"{cname} 大标题+灰色副标题", _sub_ok,
                  f"title={d.get('title')!r} size={d.get('titleSize')} sub={str(d.get('sub'))[:34]!r} subColor={d.get('subColor')}")
            check("pages", f"{cname} 右侧统计 pill 或按钮", d.get("exists") and d.get("rightHasPillOrBtn"), f"right={d.get('rightText')!r}")
            if key in ("subcontract", "finance"):
                ok_st = d.get("statCount", 0) > 0 and all(s["hasIc"] and s["icW"] == 46 for s in d.get("statCards", []))
                check("pages", f"{cname} 统计卡为横向图标块样式(46px)", ok_st,
                      f"count={d.get('statCount')} cards={[(s['hasIc'], s['icW'], str(s['label'])[:14]) for s in d.get('statCards', [])]}")
            check("pages", f"{cname} 无横向溢出", d.get("overflowX", 0) <= 0, f"overflowX={d.get('overflowX')}")

            # ---------------- 4. 扫码回归（在扫码页） ----------------
            if key == "scan":
                print("\n--- [4] 扫码识别回归 ---", flush=True)
                page.fill("#scan-input", BARCODE)
                page.press("#scan-input", "Enter")
                try:
                    page.wait_for_function("(document.querySelector('#scan-state')||{}).textContent === '已识别'", timeout=20000)
                    ok_state = True
                except Exception:
                    ok_state = False
                page.wait_for_timeout(500)
                sc = page.evaluate(SCAN_JS)
                R["scan"] = sc
                check("scan", f"输入 {BARCODE} 回车后状态=已识别", ok_state and sc["state"] == "已识别",
                      f"state={sc['state']!r} count={sc['count']!r}")
                check("scan", "识别后展示物料出入库表单", sc["detailHasForm"] and "等待扫描" not in sc["detailText"],
                      f"detail={sc['detailText'][:100]!r}")
            shot(page, f"v31-{key}.png")

        # ---------------- 5. 回归汇总 ----------------
        print("\n--- [5] 回归汇总 ---", flush=True)
        errs = [c for c in R["console"] if c["type"] == "error"]
        check("regression", "0 console error", len(errs) == 0, json.dumps(errs[:6], ensure_ascii=False))
        check("regression", "0 pageerror", len(R["pageerrors"]) == 0, json.dumps(R["pageerrors"][:6], ensure_ascii=False))
        R["regression"] = {"console_errors": errs, "console_warnings": [c for c in R["console"] if c["type"] == "warning"],
                           "pageerrors": R["pageerrors"], "net_err": R["net_err"]}
        browser.close()

    R["meta"] = {"base": BASE, "viewport": f"{VW}x{VH}", "cache_disabled": True,
                 "duration_s": round(time.time() - t0, 1), "chrome": CHROME}
    n_pass = sum(1 for c in R["checks"] if c["ok"])
    R["summary"] = {"pass": n_pass, "fail": len(R["checks"]) - n_pass}
    with open(os.path.join(OUT, "v31_result.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    print(f"\n=== 完成: {n_pass} PASS / {len(R['checks']) - n_pass} FAIL, 耗时 {round(time.time()-t0,1)}s ===", flush=True)


if __name__ == "__main__":
    main()
