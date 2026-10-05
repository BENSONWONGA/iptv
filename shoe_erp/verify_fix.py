# -*- coding: utf-8 -*-
'''部署复验(快速回归): Playwright + Chrome 直连 http://220.162.99.166:88/odk (CDP 禁用缓存)

验证两个已修复问题已消除:
  fix1: 'Identifier COMPANY has already been declared' - 重复脚本注入已修复, 页面只应有一段 app 脚本
  fix2: '$ is not a valid selector' ($ 遮蔽 jQuery) - app.js 已 IIFE 包裹, 此错应消失
功能回归 4 点:
  1) 登录(令牌预填) -> 工作台正常出数据
  2) 扫码页输入 6901234500011 回车 -> 识别 M-FAB-001
  3) 指令单中心点行 -> 抽屉打开 (openChainDrawer 全局可用)
  4) Frappe navbar/footer 仍隐藏, 无视觉残留
'''
import json, time
from playwright.sync_api import sync_playwright

BASE = 'http://220.162.99.166:88/odk'
DEMO_TOKEN = '77455c7d4b3a8fe:432939a748243fd'
CHROME = '/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome'
OUT = '/workspace/shoe_erp'
BARCODE = '6901234500011'

R = {'checks': [], 'timing': {}, 'console_errors': [], 'page_errors': [], 'load_snapshot': {},
     'fix1': {}, 'fix2': {}, 'dash': {}, 'scan': {}, 'orders': {}, 'frappe': {}, 'shots': []}

def check(phase, name, ok, detail=''):
    ok = bool(ok)
    R['checks'].append({'phase': phase, 'name': name, 'ok': ok, 'detail': str(detail)[:300]})
    print(('[PASS] ' if ok else '[FAIL] ') + phase + ' | ' + name + ('' if ok else '  --> ' + str(detail)[:250]), flush=True)

def shot(page, name):
    path = OUT + '/' + name
    page.screenshot(path=path, full_page=True)
    R['shots'].append(path)
    print('[SHOT] ' + path, flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True,
                                args=['--no-sandbox', '--disable-dev-shm-usage'])
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send('Network.enable')
    cdp.send('Network.setCacheDisabled', {'cacheDisabled': True})
    print('[i] Chrome headless launched, CDP Network.setCacheDisabled=true', flush=True)

    page.on('console', lambda m: R['console_errors'].append({'type': m.type, 'text': str(m.text)[:400]}) if m.type == 'error' else None)
    page.on('pageerror', lambda e: R['page_errors'].append(str(e)[:400]))

    # ---- 步骤1: 打开 /odk, 等 3 秒, 收集 console error / pageerror ----
    t0 = time.time()
    page.goto(BASE, wait_until='domcontentloaded', timeout=60000)
    page.wait_for_selector('#login-btn', timeout=20000)
    page.wait_for_timeout(3000)
    R['timing']['load_s'] = round(time.time() - t0, 2)
    R['load_snapshot'] = {'console_error': len(R['console_errors']), 'pageerror': len(R['page_errors'])}
    check('1-load', 'console error + pageerror = 0 (after 3s)',
          len(R['console_errors']) == 0 and len(R['page_errors']) == 0,
          json.dumps({'console': R['console_errors'], 'pageerror': R['page_errors']}, ensure_ascii=False)[:400])

    # ---- fix1: 页面只应有一段 app 脚本 ----
    fix1 = page.evaluate('''() => {
        const scripts = [...document.querySelectorAll('script')];
        const inlineApp = scripts.filter(s => !s.src && s.textContent.includes('const COMPANY'));
        const srcApp = scripts.filter(s => s.src && s.src.includes('app.js'));
        return {totalScripts: scripts.length, inlineAppScripts: inlineApp.length,
                appSrcReferences: srcApp.length, appScriptCount: inlineApp.length + srcApp.length,
                srcList: scripts.filter(s => s.src).map(s => s.src.split('/').pop()).slice(0, 12)};
    }''')
    R['fix1'] = fix1
    check('fix1', 'exactly ONE app script (duplicate injection gone)', fix1['appScriptCount'] == 1,
          'inline=' + str(fix1['inlineAppScripts']) + ' srcRef=' + str(fix1['appSrcReferences']) + ' totalScripts=' + str(fix1['totalScripts']))

    # ---- fix2: IIFE 后全局导出未破坏 ----
    fix2 = page.evaluate('''() => ({openERP: typeof window.openERP, openChainDrawer: typeof window.openChainDrawer})''')
    R['fix2'] = fix2
    check('fix2', 'window.openERP is function (IIFE export intact)', fix2['openERP'] == 'function', json.dumps(fix2))
    check('fix2', 'window.openChainDrawer is function (IIFE export intact)', fix2['openChainDrawer'] == 'function', json.dumps(fix2))

    # ---- 步骤2: 登录(令牌已预填) -> 工作台出数据 ----
    token = page.evaluate('''() => ((document.querySelector('#login-token')||{}).value || 'EMPTY')''')
    check('2-login', 'demo token pre-filled', token == DEMO_TOKEN, token[:18])
    t1 = time.time()
    page.click('#login-btn')
    try:
        page.wait_for_selector('.hero-banner', timeout=40000)
        page.wait_for_selector('.stat-card .stat-value', timeout=20000)
        page.wait_for_timeout(2500)
        R['timing']['login_to_dash_s'] = round(time.time() - t1, 2)
        check('2-login', 'login -> dashboard rendered', True, str(R['timing']['login_to_dash_s']) + 's')
    except Exception as e:
        check('2-login', 'login -> dashboard rendered', False, str(e)[:200])
    errbox = page.evaluate('''() => ((document.querySelector('#login-err')||{}).textContent || '')''')
    if errbox:
        check('2-login', 'login error box empty', False, errbox)

    dash = page.evaluate('''() => ({
        heroText: (document.querySelector('.hero-banner h2')||{}).textContent || '',
        statCount: document.querySelectorAll('.stat-card').length,
        statVals: [...document.querySelectorAll('.stat-card')].map(c => ({
            label: (c.querySelector('.stat-label')||{}).textContent || '',
            value: (c.querySelector('.stat-value')||{}).textContent || ''}))})''')
    R['dash'] = dash
    check('2-login', 'dashboard 4 stat cards', dash['statCount'] == 4, 'n=' + str(dash['statCount']))
    vals = {v['label']: v['value'] for v in dash['statVals']}
    empty = [v['label'] for v in dash['statVals'] if v['value'].strip() in ('', '-', '--')]
    check('2-login', 'stat cards all have data', len(empty) == 0, json.dumps(vals, ensure_ascii=False)[:250])
    shot(page, 'final-dashboard.png')

    # ---- 步骤3: 扫码页输入 6901234500011 回车 -> 识别 M-FAB-001 ----
    page.evaluate('''() => { location.hash = '#/scan'; }''')
    try:
        page.wait_for_selector('#scan-input', timeout=20000)
        page.fill('#scan-input', BARCODE)
        page.press('#scan-input', 'Enter')
        page.wait_for_selector('.scan-item', timeout=25000)
        page.wait_for_timeout(800)
        scan = page.evaluate('''() => ({
            state: ((document.querySelector('#scan-state')||{}).textContent || ''),
            item: ((document.querySelector('.scan-item b')||{}).textContent || ''),
            pill: ((document.querySelector('.scan-item .pill')||{}).textContent || '')})''')
        R['scan'] = scan
        check('3-scan', 'barcode 6901234500011 recognized', '已识别' in scan['state'], scan['state'])
        check('3-scan', 'material M-FAB-001 (scan function intact)', 'M-FAB-001' in scan['item'], scan['item'][:60])
        shot(page, 'final-scan.png')
    except Exception as e:
        check('3-scan', 'scan recognize M-FAB-001', False, str(e)[:200])

    # ---- 步骤4: 指令单中心点行 -> 抽屉打开 ----
    page.evaluate('''() => { location.hash = '#/orders'; }''')
    try:
        page.wait_for_selector('.tbl tbody tr', timeout=30000)
        rows = page.evaluate('''() => document.querySelectorAll('.tbl tbody tr').length''')
        check('4-orders', 'orders table has rows', rows > 0, 'rows=' + str(rows))
        page.click('.tbl tbody tr:first-child')
        page.wait_for_selector('.drawer .chain-node', timeout=30000)
        page.wait_for_timeout(1200)
        nodes = page.evaluate('''() => ({total: document.querySelectorAll('.drawer .chain-node').length,
            done: document.querySelectorAll('.drawer .chain-node.done').length,
            hd: ((document.querySelector('.drawer-hd h3')||{}).textContent || '')})''')
        R['orders'] = dict({'rows': rows}, **nodes)
        check('4-orders', 'drawer opens on row click (openChainDrawer global)', nodes['total'] >= 1,
              'chainNodes=' + str(nodes['total']) + ' hd=' + str(nodes['hd'])[:36])
        check('4-orders', 'drawer 14-step chain', nodes['total'] == 14,
              'nodes=' + str(nodes['total']) + ' done=' + str(nodes['done']))
        shot(page, 'final-drawer.png')
        page.keyboard.press('Escape')
        page.wait_for_timeout(400)
    except Exception as e:
        check('4-orders', 'drawer opens on row click', False, str(e)[:200])

    # ---- 步骤5: Frappe navbar/footer 仍隐藏, 无视觉残留 ----
    frappe = page.evaluate('''() => {
        const sels = ['nav.navbar', '.navbar', '.page-breadcrumbs', 'footer', '.web-footer',
                      '.page-header-wrapper', '.standard-navbar', '.standard-footer'];
        const res = {}; const visible = [];
        for (const s of sels) {
            const el = document.querySelector(s);
            if (!el) { res[s] = 'absent'; continue; }
            const cs = getComputedStyle(el);
            if (cs.display === 'none') res[s] = 'hidden';
            else { res[s] = 'VISIBLE:' + cs.display; if (el.offsetWidth > 0 && el.offsetHeight > 0) visible.push(s); }
        }
        const b = getComputedStyle(document.body);
        return {sels: res, visibleResidue: visible, bodyPadding: b.paddingTop + '/' + b.paddingBottom, bodyBg: b.backgroundColor};
    }''')
    R['frappe'] = frappe
    check('5-frappe', 'navbar/footer hidden or absent (no visual residue)', len(frappe['visibleResidue']) == 0,
          json.dumps(frappe['sels'], ensure_ascii=False)[:280])

    # ---- 汇总: 全程 console ----
    R['timing']['total_s'] = round(time.time() - t0, 2)
    joined = ' | '.join([c['text'] for c in R['console_errors']] + R['page_errors'])
    R['fix1']['companyErrorGone'] = ('COMPANY' not in joined) and ('already been declared' not in joined)
    R['fix2']['selectorErrorGone'] = ('$ is not a valid selector' not in joined)
    check('fix1', 'no COMPANY redeclare console error', R['fix1']['companyErrorGone'],
          json.dumps([c for c in R['console_errors'] if 'COMPANY' in c['text']][:3], ensure_ascii=False))
    check('fix2', 'no dollar-is-not-a-valid-selector console error', R['fix2']['selectorErrorGone'],
          json.dumps([c for c in R['console_errors'] if 'valid selector' in c['text']][:3], ensure_ascii=False))
    check('6-console', 'console errors total = 0 (whole session)', len(R['console_errors']) == 0,
          json.dumps(R['console_errors'], ensure_ascii=False)[:300])
    check('6-console', 'pageerror total = 0 (whole session)', len(R['page_errors']) == 0,
          json.dumps(R['page_errors'], ensure_ascii=False)[:300])

    browser.close()

json.dump(R, open(OUT + '/verify_fix_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
fails = [c for c in R['checks'] if not c['ok']]
n = len(R['checks'])
print('', flush=True)
print('========== VERIFY RESULT: ' + str(n - len(fails)) + '/' + str(n) + ' PASS ==========', flush=True)
if fails:
    print('FAILED: ' + json.dumps(fails, ensure_ascii=False)[:900], flush=True)
print('TIMING: ' + json.dumps(R['timing'], ensure_ascii=False), flush=True)
print('ConsoleError(load3s)=' + str(R['load_snapshot']['console_error']) + ' PageError(load3s)=' + str(R['load_snapshot']['pageerror']) + ' ConsoleError(session)=' + str(len(R['console_errors'])) + ' PageError(session)=' + str(len(R['page_errors'])), flush=True)
print('ResultJSON: ' + OUT + '/verify_fix_result.json', flush=True)
