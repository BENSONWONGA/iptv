# -*- coding: utf-8 -*-
# 技转模块示例数据：A-001 的工艺流程/确认单/试做单/进度
import json
import urllib.request

URL = 'http://127.0.0.1:8069'


def call(service, method, *args):
    payload = {'jsonrpc': '2.0', 'method': 'call',
               'params': {'service': service, 'method': method, 'args': list(args)}}
    req = urllib.request.Request(
        URL + '/jsonrpc', data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'})
    out = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    if 'error' in out:
        raise RuntimeError(out['error']['data'].get('message', 'unknown')[:200])
    return out['result']


uid = call('common', 'authenticate', 'odoo20', 'admin', 'admin', {})
print('登录 uid=%s' % uid)


def ex(model, method, *args, **kw):
    return call('object', 'execute_kw', 'odoo20', uid, 'admin',
                model, method, list(args), kw)


a001 = ex('product.template', 'search', [('default_code', '=', 'A-001')], limit=1)
bom = ex('mrp.bom', 'search', [('product_tmpl_id', '=', a001[0])], limit=1)
cust = ex('res.partner', 'search', [('name', '=', '福州华峰鞋业连锁')], limit=1)
a001[0] = a001[0]
print('A-001模板 %s | BOM %s | 客户 %s' % (a001[0], bom[0] if bom else '-', cust[0] if cust else '-'))

# 1) 部件工艺流程单
exist = ex('odk.tech.routing', 'search', [('style_id', '=', a001[0])], limit=1)
if exist:
    gid = exist[0]
    print('工艺流程单已存在', gid)
else:
    gid = ex('odk.tech.routing', 'create',
             {'name': 'GY-A001', 'style_id': a001[0], 'note': 'A-001 全鞋工艺流程'})
    specs = [
        ('cutting', '裁断', '电脑裁断机', '注塑片材利用率'),
        ('stitching', '鞋面针车', '针车一组', '车线整齐无浮线'),
        ('lasting', '前帮/中帮/后帮', '成型线一工位', '钳帮到位'),
        ('outsole', '大底贴合', '压底机', '压力/温度按SOP'),
        ('assembly', '烘干定型', '烘箱', '温度60-70度'),
        ('packing', '成品质检包装', '包装组', '外观全检'),
    ]
    for seq, (comp, proc, wc, desc) in enumerate(specs, start=1):
        ex('odk.tech.routing.line', 'create',
           {'routing_id': gid, 'sequence': seq * 10, 'component': comp,
            'process': proc, 'work_center': wc, 'cycle_time': 30.0,
            'description': desc})
    print('工艺流程单新建', gid, '含6道工序')

# 2) 量产确认单
exist = ex('odk.tech.confirm', 'search', [('style_id', '=', a001[0])], limit=1)
if exist:
    cid = exist[0]
    print('量产确认单已存在', cid)
else:
    cid = ex('odk.tech.confirm', 'create',
             {'style_id': a001[0], 'customer_id': cust[0] if cust else False,
              'bom_id': bom[0] if bom else False, 'routing_id': gid,
              'note': 'A-001 首单量产确认'})
    print('量产确认单新建', cid)
ex('odk.tech.confirm', 'write', [cid], {'state': 'confirmed'})
print('量产确认单状态 -> 已确认')

# 3) 试做单（黑色 42 码 12 双）
vs = ex('product.product', 'search_read',
        [('product_tmpl_id', '=', a001[0])], ['display_name'], limit=50)
v42 = [v['id'] for v in vs if ('黑色' in v['display_name'] and '42' in v['display_name'])]
v42 = v42[:1]
if v42:
    exist = ex('odk.tech.trial', 'search', [('confirm_id', '=', cid)], limit=1)
    if not exist:
        tid = ex('odk.tech.trial', 'create',
                 {'confirm_id': cid, 'product_id': v42[0], 'product_qty': 12,
                  'result_note': '产前试做12双，验证用量与工艺'})
        ex('odk.tech.trial', 'write', [tid], {'state': 'doing'})
        print('试做单新建', tid)
else:
    print('未找到黑色42码变体，跳过试做单')

# 4) 试做进度（AOK 阶段）
exist = ex('odk.tech.progress', 'search', [('style_id', '=', a001[0])], limit=1)
if not exist:
    ex('odk.tech.progress', 'create',
       {'style_id': a001[0], 'customer_id': cust[0] if cust else False,
        'season': '2026春季', 'stage': 'aok', 'note': '客户AOK签样进行中'})
    print('试做进度新建（AOK阶段）')

print('DONE')
