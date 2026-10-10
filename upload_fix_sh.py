#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 把 odk_dispatch_fix.sh 上传为线上 Odoo 公开附件 → 生成服务器端一条命令
import base64
import json
import urllib.request

URL = 'http://220.162.99.166:88'
DB, USER, PWD = 'odk_erp', 'admin', 'admin'


def call(service, method, *args):
    payload = {'jsonrpc': '2.0', 'method': 'call',
               'params': {'service': service, 'method': method, 'args': list(args)}}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(URL + '/jsonrpc', data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as resp:
        out = json.loads(resp.read().decode('utf-8'))
    if 'error' in out:
        raise RuntimeError(str(out['error'])[:600])
    return out.get('result')


uid = call('common', 'authenticate', DB, USER, PWD, {})
print('[OK] 线上登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    if kw:
        return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args), kw)
    return call('object', 'execute_kw', DB, uid, PWD, model, method, list(args))


SH = '/workspace/odk_dispatch_fix.sh'
raw = open(SH, 'rb').read()
datas = base64.b64encode(raw).decode()

# 删除旧的同名/测试附件（重跑幂等）
old = ex('ir.attachment', 'search',
         [('name', 'in', ('odk_dispatch_fix.sh', 't1.txt', 't2.txt', 't3.txt'))],
         limit=20)
if old:
    ex('ir.attachment', 'unlink', old)
    print('[0] 已清理旧附件 %d 个' % len(old))

# Odoo 20：datas 不可直写，用 db_datas 直写 + type=binary
att_id = ex('ir.attachment', 'create', {
    'name': 'odk_dispatch_fix.sh',
    'db_datas': datas,
    'mimetype': 'text/x-shellscript',
    'public': True,
    'type': 'binary',
})
print('[1] 附件已创建 id=%s' % att_id)

# 验证外网可下载（无登录态）
dl = URL + '/web/content/%s?download=true' % att_id
with urllib.request.urlopen(dl, timeout=60) as resp:
    body = resp.read()
print('[2] 下载验证: HTTP %s | %d 字节 | 与本地一致: %s'
      % (resp.status, len(body), body == raw))
assert body == raw, '下载内容与本地不一致!'
print()
print('下载地址: %s' % dl)
print()
print('===== 服务器端执行命令（在服务器终端粘贴这一行） =====')
print("cd /www/wwwroot && wget -q '%s' -O odk_fix.sh && bash odk_fix.sh" % dl)
print('========================================================')
