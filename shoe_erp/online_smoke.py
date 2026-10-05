# -*- coding: utf-8 -*-
"""Online deploy smoke test: Playwright + Chrome direct to http://220.162.99.166:88/files/odk.html"""
import json, time
from playwright.sync_api import sync_playwright

BASE = 'http://220.162.99.166:88/files/odk.html'
DEMO_TOKEN = '77455c7d4b3a8fe:f36c1a4b10e8b5e'
CHROME = '/root/.cache/puppeteer/chrome/linux-151.0.7922.71/chrome-linux64/chrome'
OUT = '/workspace/shoe_erp'
BARCODE = '6901234500011'

R = {'checks': [], 'timing': {}, 'login': {}, 'dash': {}, 'orders': {}, 'scan': {}, 'finance': {}, 'prod': {},
     'console_errors': [], 'page_errors': [], 'net_failed': [], 'http_bad': [], 'api_calls': [], 'cors_issues': [], 'shots': []}

def check(phase, name, ok, detail=''):
    ok = bool(ok)
    R['checks'].append({'phase': phase, 'name': name, 'ok': ok, 'detail': str(detail)[:300]})
    print(('[PASS] ' if ok else '[FAIL] ') + phase + ' | ' + name + ('' if ok else '  --> ' + str(detail)[:220]), flush=True)

def shot(page, name):
    path = OUT + '/' + name
    page.screenshot(path=path, full_page=True)
    R['shots'].append(path)
    print('[SHOT] ' + path, flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROME, headless=True, args=['--proxy-server=http://127.0.0.1:18080', '--no-sandbox', '--disable-dev-shm-usage'])
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send('Network.enable')
    cdp.send('Network.setCacheDisabled', {'cacheDisabled': True})
    print('[i] CDP Network.setCacheDisabled enabled, --no-proxy-server', flush=True)
    page.on('console', lambda m: R['console_errors'].append({'type': m.type, 'text': str(m.text)[:400]}) if m.type in ('error', 'warning') else None)
    page.on('pageerror', lambda e: R['page_errors'].append(str(e)[:400]))
    page.on('requestfailed', lambda r: R['net_failed'].append({'url': r.url, 'err': str(r.failure)[:200]}))
    def on_resp(resp):
        u = resp.url
        if '/api/' in u:
            R['api_calls'].append({'url': u.split('88')[-1][:110], 'status': resp.status})
        if resp.status in (401, 403, 500, 502):
            R['http_bad'].append({'url': u[:150], 'status': resp.status})
    page.on('response', on_resp)

    t0 = time.time()
    page.goto(BASE, wait_until='domcontentloaded', timeout=60000)
    R['timing']['goto_s'] = round(time.time() - t0, 2)
    page.wait_for_selector('#login-btn', timeout=20000)
    page.wait_for_timeout(800)
    R['timing']['login_ready_s'] = round(time.time() - t0, 2)
    login = page.evaluate("""() => ({
        bodyBg: getComputedStyle(document.body).backgroundColor,
        gridCols: getComputedStyle(document.querySelector('.login-view')).gridTemplateColumns,
        hasLeft: !!document.querySelector('.login-left'),
        slogan: (document.querySelector('.ll-hero h1')||{}).textContent || '',
        procCount: document.querySelectorAll('.ll-process span').length,
        formTitle: (document.querySelector('.lr-card h2')||{}).textContent || '',
        tokenValue: (document.querySelector('#login-token')||{}).value || '',
        btnText: (document.querySelector('#login-btn')||{}).textContent.trim() || '',
        url: location.href,
    })""")
    R['login'] = login
    check('1-loginpage', 'dark charcoal bg #0C1118', 'rgb(12, 17, 24)' in login['bodyBg'], login['bodyBg'])
    check('1-loginpage', 'split layout 52/48', login['hasLeft'] and bool(login['gridCols']), login['gridCols'])
    check('1-loginpage', 'slogan yi-shuang-xie', chr(19968)+chr(21452)+chr(38795) in login['slogan'], login['slogan'][:30])
    check('1-loginpage', 'process axis 6 pills', login['procCount'] == 6, 'n=' + str(login['procCount']))
    check('1-loginpage', 'form title jin-ru-jia-shi-cang', chr(36827)+chr(20837)+chr(39550)+chr(39542)+chr(33329) in login['formTitle'], login['formTitle'])
    check('1-loginpage', 'token auto-filled', login['tokenValue'] == DEMO_TOKEN, login['tokenValue'][:16] + '...')
    shot(page, 'online-login.png')

    t1 = time.time()
    page.click('#login-btn')
    try:
        page.wait_for_selector('.hero-banner', timeout=40000)
        page.wait_for_selector('.stat-card .stat-value', timeout=20000)
        page.wait_for_timeout(2500)
        R['timing']['login_to_dash_s'] = round(time.time() - t1, 2)
        check('2-login', 'same-origin API login -> dashboard', True, R['timing']['login_to_dash_s'])
    except Exception as e:
        R['timing']['login_to_dash_s'] = round(time.time() - t1, 2)
        check('2-login', 'same-origin API login -> dashboard', False, str(e)[:200])
    errbox = page.evaluate("() => (document.querySelector('#login-err')||{}).textContent || ''")
    if errbox: check('2-login', 'login error box', False, errbox)
    shot(page, 'online-dashboard.png')

    dash = page.evaluate("""() => ({
        heroText: (document.querySelector('.hero-banner h2')||{}).textContent || '',
        heroChips: [...document.querySelectorAll('.hb-chip b')].map(b => b.textContent.trim()),
        statCount: document.querySelectorAll('.stat-card').length,
        statVals: [...document.querySelectorAll('.stat-card')].map(c => ({
            label: (c.querySelector('.stat-label')||{}).textContent || '',
            value: (c.querySelector('.stat-value')||{}).textContent || '',
        })),
        fcNum: (document.querySelector('.fc-num i')||{}).textContent || '',
        fcTotal: (document.querySelector('.fc-num')||{}).textContent || '',
        fbDone: document.querySelectorAll('.fb-chip.done').length,
        fbTotal: document.querySelectorAll('.fb-step').length,
        perf: performance.getEntriesByType('navigation').map(e => ({dur: Math.round(e.duration), dcl: Math.round(e.domContentLoadedEventEnd), load: Math.round(e.loadEventEnd), ttfb: Math.round(e.responseStart)})),
    })""")
    R['dash'] = dash
    check('3-dashboard', 'welcome banner', bool(dash['heroText']), dash['heroText'][:20])
    check('3-dashboard', 'banner number chips', len(dash['heroChips']) >= 3, str(dash['heroChips']))
    check('3-dashboard', '4 stat cards', dash['statCount'] == 4, 'n=' + str(dash['statCount']))
    vals = {v['label']: v['value'] for v in dash['statVals']}
    jinXing = vals.get(chr(36827)+chr(34892)+chr(20013)+chr(25351)+chr(20196)+chr(21333), '-')
    chengPin = vals.get(chr(25104)+chr(21697)+chr(20179)+chr(24211)+chr(23384), '-')
    check('3-dashboard', 'active orders has data', jinXing not in ('-', '0', '0.0'), str(jinXing))
    check('3-dashboard', 'fg warehouse qty has data', chengPin not in ('-', '0', '0.0'), str(chengPin))
    check('3-dashboard', 'flow 14/14 golden nodes', dash['fcNum'] == '14' and dash['fbDone'] == 14 and dash['fbTotal'] == 14,
          str(dash['fcNum']) + ' done=' + str(dash['fbDone']) + '/' + str(dash['fbTotal']))

    page.evaluate("location.hash='#/orders'")
    try:
        page.wait_for_selector('.tbl tbody tr', timeout=30000)
        rows = page.evaluate("document.querySelectorAll('.tbl tbody tr').length")
        check('4-orders', 'table has rows', rows > 0, 'rows=' + str(rows))
        page.click('.tbl tbody tr:first-child')
        page.wait_for_selector('.drawer .chain-node', timeout=30000)
        page.wait_for_timeout(1200)
        nodes = page.evaluate("({total: document.querySelectorAll('.drawer .chain-node').length, done: document.querySelectorAll('.drawer .chain-node.done').length, hd: (document.querySelector('.drawer-hd h3')||{}).textContent||''})")
        R['orders'] = dict({'rows': rows}, **nodes)
        check('4-orders', 'drawer 14-step chain', nodes['total'] == 14, 'nodes=' + str(nodes['total']))
        shot(page, 'online-drawer.png')
        page.keyboard.press('Escape')
        page.wait_for_timeout(400)
    except Exception as e:
        check('4-orders', 'drawer 14-step chain', False, str(e)[:200])

    page.evaluate("location.hash='#/scan'")
    try:
        page.wait_for_selector('#scan-input', timeout=20000)
        page.fill('#scan-input', BARCODE)
        page.press('#scan-input', 'Enter')
        page.wait_for_selector('.scan-item', timeout=25000)
        page.wait_for_timeout(600)
        scan = page.evaluate("""() => ({
            state: (document.querySelector('#scan-state')||{}).textContent || '',
            item: (document.querySelector('.scan-item b')||{}).textContent || '',
            pill: (document.querySelector('.scan-item .pill')||{}).textContent || '',
        })""")
        R['scan'] = scan
        check('5-scan', 'barcode recognized', chr(24050)+chr(35782)+chr(21035) in scan['state'], scan['state'])
        check('5-scan', 'material M-FAB-001', 'M-FAB-001' in scan['item'], scan['item'][:40])
        shot(page, 'online-scan.png')
    except Exception as e:
        check('5-scan', 'scan recognize', False, str(e)[:200])

    page.evaluate("location.hash='#/finance'")
    try:
        page.wait_for_selector('#page .stat-card', timeout=30000)
        page.wait_for_timeout(1500)
        fin = page.evaluate("""() => ({
            cards: [...document.querySelectorAll('#page .stat-card')].map(c => (c.querySelector('.stat-label')||{}).textContent + '=' + (c.querySelector('.stat-value')||{}).textContent),
            tblRows: document.querySelectorAll('#page .tbl tbody tr, #page table tbody tr').length,
        })""")
        R['finance'] = fin
        check('6-finance', '3 stat cards', len(fin['cards']) == 3, str(fin['cards']))
        check('6-finance', 'recon table rows', fin['tblRows'] > 0, 'rows=' + str(fin['tblRows']))
    except Exception as e:
        check('6-finance', 'finance page', False, str(e)[:200])

    page.evaluate("location.hash='#/production'")
    try:
        page.wait_for_selector('#page .grid .card-bd, #page .grid > .card', timeout=30000)
        page.wait_for_timeout(1500)
        prod = page.evaluate("""() => {
            const bars = [...document.querySelectorAll('#page .grid > .card > div[style*=height] > div[style*=width]')];
            const woCards = document.querySelectorAll('#page .grid > .card').length;
            const amber = bars.filter(b => ((b.getAttribute('style')||'')).includes('#FFB020') || ((b.getAttribute('style')||'')).includes('#DB8A00')).length;
            return {woCards, bars: bars.length, amber,
                sample: bars.length ? (bars[0].getAttribute('style')||'').slice(0,120) : ''};
        }""")
        R['prod'] = prod
        check('7-production', 'work order cards', prod['woCards'] > 0, 'cards=' + str(prod['woCards']))
        check('7-production', 'amber progress bars', prod['amber'] > 0, 'amber=' + str(prod['amber']) + '/' + str(prod['bars']))
    except Exception as e:
        check('7-production', 'production page', False, str(e)[:200])

    R['timing']['total_s'] = round(time.time() - t0, 2)
    cors = [c for c in R['console_errors'] if 'CORS' in c['text'] or 'Access-Control' in c['text'] or 'cors' in c['text'].lower()]
    netcors = [n for n in R['net_failed'] if 'CORS' in str(n.get('err', ''))]
    R['cors_issues'] = cors + netcors
    api_ok = [a for a in R['api_calls'] if a['status'] == 200]
    check('8-network', 'api all 200 (' + str(len(R['api_calls'])) + ' calls)', len(R['api_calls']) > 0 and len(api_ok) == len(R['api_calls']), str(len(api_ok)) + '/' + str(len(R['api_calls'])))
    check('8-network', 'no CORS errors (same-origin)', len(cors) == 0 and len(netcors) == 0, str(R['cors_issues'])[:200])
    check('8-network', 'no 401/403/5xx', len(R['http_bad']) == 0, str(R['http_bad'])[:200])
    check('8-network', 'no failed requests', len(R['net_failed']) == 0, str(R['net_failed'])[:200])
    err_only = [c for c in R['console_errors'] if c['type'] == 'error']
    check('8-network', 'no console errors', len(err_only) == 0, str(err_only)[:300])
    browser.close()

json.dump(R, open(OUT + '/online_smoke_result.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
fails = [c for c in R['checks'] if not c['ok']]
print('', flush=True)
print('========== SMOKE RESULT: ' + str(len(R['checks']) - len(fails)) + '/' + str(len(R['checks'])) + ' PASS ==========', flush=True)
if fails:
    print('FAILED: ' + json.dumps(fails, ensure_ascii=False)[:600], flush=True)
print('TIMING: ' + json.dumps(R['timing'], ensure_ascii=False), flush=True)
print('API calls: ' + str(len(R['api_calls'])) + ', all200=' + str(len([a for a in R['api_calls'] if a['status']==200]) == len(R['api_calls'])), flush=True)
print('Saved: ' + OUT + '/online_smoke_result.json', flush=True)
