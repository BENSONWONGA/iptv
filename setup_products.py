#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""奥登科户外：创建网站商品分类 + 12款户外鞋产品（含图片与尺码变体）"""
import base64
import io
import json

import requests
from PIL import Image

HOST = 'http://220.162.99.166:9000'
DB, USER, PASS = 'benson', 'admin', 'Benson@2026'
ASSETS = '/workspace/site_assets'

s = requests.Session()


def rpc(model, method, args=None, kwargs=None, timeout=600):
    r = s.post(HOST + '/web/dataset/call_kw', json={
        'jsonrpc': '2.0', 'method': 'call',
        'params': {'model': model, 'method': method, 'args': args or [], 'kwargs': kwargs or {}},
    }, timeout=timeout)
    d = r.json()
    if 'error' in d:
        raise RuntimeError('%s/%s: %s' % (model, method, json.dumps(d['error'], ensure_ascii=False)[:400]))
    return d['result']


r = s.post(HOST + '/web/session/authenticate', json={
    'jsonrpc': '2.0', 'params': {'db': DB, 'login': USER, 'password': PASS}}, timeout=60)
uid = r.json()['result']['uid']
print('RPC 登录 ✓')

# ---------- 工具 ----------
def img_b64(path, max_side=900, quality=85):
    im = Image.open(path).convert('RGB')
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=quality)
    return base64.b64encode(buf.getvalue()).decode()


def get_or_create(model, domain, vals):
    recs = rpc(model, 'search', [domain])
    if recs:
        return recs[0]
    return rpc(model, 'create', [vals])


# ---------- 1. 网站商品分类 ----------
CATS = ['徒步系列', '越野跑系列', '登山系列', '溯溪系列', '休闲户外']
cat_ids = {}
for c in CATS:
    cat_ids[c] = get_or_create('product.public.category', [('name', '=', c)],
                               {'name': c, 'website_id': 1})
print('分类:', cat_ids)

# ---------- 2. 尺码属性 ----------
attr_id = get_or_create('product.attribute', [('name', '=', '尺码')],
                        {'name': '尺码', 'display_type': 'select', 'create_variant': 'always',
                         'sequence': 1})
size_vals = []
for size in ['39', '40', '41', '42', '43', '44', '45']:
    vid = get_or_create('product.attribute.value',
                        [('name', '=', size), ('attribute_id', '=', attr_id)],
                        {'name': size, 'attribute_id': attr_id, 'sequence': int(size) - 38})
    size_vals.append(vid)
print('尺码属性:', attr_id, '值:', size_vals)

# ---------- 3. 产品数据 ----------
PRODUCTS = [
    dict(name='奥登科·征途Pro 中帮徒步鞋', cat='徒步系列', price=699, cost=210, img='p01_zhengtu.jpg',
         code='ADK-H001',
         short='AK-TEX防水透气膜 · 魔爪耐磨大底 · 中帮踝部支撑',
         desc='征途Pro 是奥登科户外的经典中帮徒步鞋，采用头层牛皮与防泼水网布拼接鞋面，内置 AK-TEX 防水透气膜，从容应对溪流碎石与多变天气。EVA双密度中底提供长效缓震，搭配 5mm 深齿魔爪橡胶大底，湿滑岩面依然抓地稳健。',
         weight=1.05, seq=10),
    dict(name='奥登科·岚风GTX 低帮徒步鞋', cat='徒步系列', price=549, cost=165, img='p02_lanfeng.jpg',
         code='ADK-H002',
         short='轻量网布鞋面 · 快速系带系统 · 单只仅320g',
         desc='岚风为轻装快行而设计：一体织高弹网布鞋面透气包裹，快速系带系统一拉即紧。前掌弯曲凹槽让步态自然流畅，是日常郊山与轻装徒步的高性价比之选。',
         weight=0.68, seq=11),
    dict(name='奥登科·沙漠行者 徒步靴', cat='徒步系列', price=659, cost=200, img='p07_shamo.jpg',
         code='ADK-H003',
         short='翻毛皮鞋面 · 克里佩大底 · 越野通勤两相宜',
         desc='沙漠行者以经典沙漠靴为原型，升级户外性能：头层翻毛皮鞋面坚韧透气，缓震克里佩大底轻弹静音，城市通勤与周末山野自由切换。',
         weight=0.82, seq=12),
    dict(name='奥登科·铁途 重装徒步靴', cat='徒步系列', price=899, cost=280, img='p11_tietu.jpg',
         code='ADK-H004',
         short='全粒面牛皮 · 全掌TPU抗扭片 · 重装长途首选',
         desc='铁途为多日重装徒步打造：2.4mm 全粒面牛皮鞋面配全包橡胶防撞条，历经碎石考验；全掌 TPU 抗扭片与 PU 中底组合，背负 20kg 行囊依然稳定支撑，一步一履皆安心。',
         weight=1.42, seq=13),
    dict(name='奥登科·猎鹰TX 越野跑鞋', cat='越野跑系列', price=499, cost=150, img='p03_lieying.jpg',
         code='ADK-T001',
         short='6mm鲨齿大底 · 前掌推进模块 · 抓地爆发兼顾',
         desc='猎鹰TX 为山地竞速而生：激进的 6mm 鲨齿大底咬合泥地碎石，前掌内置推进模块助力蹬伸，超轻 Race 网布鞋面紧密包裹，让每一次冲坡都信心十足。',
         weight=0.55, seq=20),
    dict(name='奥登科·云驰 缓震越野跑鞋', cat='越野跑系列', price=459, cost=138, img='p04_yunchi.jpg',
         code='ADK-T002',
         short='超临界发泡中底 · 38mm堆栈 · 长距离缓震专家',
         desc='云驰主打长效缓震：超临界发泡中底轻弹耐疲劳，38mm 后掌堆栈有效化解长距离冲击；宽楦鞋仓适配亚洲脚型，超长距离也能保持舒适。',
         weight=0.62, seq=21),
    dict(name='奥登科·疾风 竞速越野跑鞋', cat='越野跑系列', price=599, cost=185, img='p10_jifeng.jpg',
         code='ADK-T003',
         short='全掌碳板 · 镂空鞋面 · 为破纪录而生',
         desc='疾风是奥登科最速战靴：全掌碳纤维推进板结合双密度泡棉，回弹率高达 78%；轻量镂空 MONO 纱鞋面配合精准锁定系统，专为 50km 以上竞速与 ITRA 赛事打造。',
         weight=0.49, seq=22),
    dict(name='奥登科·巅峰8000 高山登山靴', cat='登山系列', price=1899, cost=620, img='p05_dianfeng.jpg',
         code='ADK-M001',
         short='双层靴体 · 全自动卡扣兼容 · -40℃极寒实测',
         desc='巅峰8000 面向高海拔远征：外靴采用一体注塑 PE 壳体，兼容全自动冰爪；内靴为真空反光保暖结构，-40℃ 环境实测保持足部温度，是 6000 米以上雪山的可靠伙伴。',
         weight=2.35, seq=30),
    dict(name='奥登科·极地雪线 保暖登山靴', cat='登山系列', price=1299, cost=420, img='p08_jidi.jpg',
         code='ADK-M002',
         short='一体化雪套 · 200g新雪丽棉 · 冰爪兼容',
         desc='极地雪线为冬季雪山与冰雪徒步设计：一体化防雪套杜绝灌雪，200g 新雪丽保暖棉锁住温度，Vibram 类 Arctic 冰爪大底专攻硬雪坡，冬季登山一步到位。',
         weight=1.58, seq=31),
    dict(name='奥登科·岩雀 攀登接近鞋', cat='登山系列', price=389, cost=120, img='p12_yanque.jpg',
         code='ADK-M003',
         short='攀级橡胶 · 精准贴楦 · 抱石 scrambling 利器',
         desc='岩雀采用专业攀级粘性橡胶大底，湿滑岩壁摩擦力出色；低帮贴楦设计让脚掌感知细腻精准， 第四类 scrambing 地形与抱石接近路线的理想选择。',
         weight=0.58, seq=32),
    dict(name='奥登科·溯溪者 水陆两栖鞋', cat='溯溪系列', price=329, cost=98, img='p06_suxi.jpg',
         code='ADK-W001',
         short='17孔速排水 · 裸足感网布 · 溪降峡谷专用',
         desc='溯溪者专为峡谷溪降打造：大底与鞋侧 17 个排水孔实现"入水即排"，速干网布杜绝闷湿；锯齿状排水纹大底在青苔石面依然稳健，是夏季溪谷线路的清凉装备。',
         weight=0.52, seq=40),
    dict(name='奥登科·轻野 休闲户外鞋', cat='休闲户外', price=399, cost=118, img='p09_qingye.jpg',
         code='ADK-C001',
         short='都市山野无缝切换 · 柔软缓震 · 百搭造型',
         desc='轻野模糊了城市与山野的边界：极简外观低调百搭，隐藏式防水膜与缓震大底让说走就走的郊游说走就走，日常通勤同样舒适胜任。',
         weight=0.61, seq=50),
]

created = []
for p in PRODUCTS:
    name = p['name']
    exist = rpc('product.template', 'search', [[('name', '=', name)]])
    b64 = img_b64('%s/%s' % (ASSETS, p['img']), max_side=900)
    vals = {
        'name': name,
        'default_code': p['code'],
        'list_price': p['price'],
        'standard_price': p['cost'],
        'type': 'consu',
        'is_storable': False,
        'sale_ok': True,
        'purchase_ok': False,
        'is_published': True,
        'website_sequence': p['seq'],
        'description_sale': p['short'],
        'description_ecommerce': '<p>%s</p>' % p['desc'],
        'public_categ_ids': [(6, 0, [cat_ids[p['cat']]])],
        'weight': p['weight'],
        'image_1920': b64,
    }
    if exist:
        rpc('product.template', 'write', [exist, vals])
        tmpl_id = exist[0]
        action = 'updated'
    else:
        tmpl_id = rpc('product.template', 'create', [vals])
        action = 'created'
    # 尺码属性行（幂等）
    lines = rpc('product.template.attribute.line', 'search',
                [[('product_tmpl_id', '=', tmpl_id), ('attribute_id', '=', attr_id)]])
    if not lines:
        rpc('product.template.attribute.line', 'create', [{
            'product_tmpl_id': tmpl_id,
            'attribute_id': attr_id,
            'value_ids': [(6, 0, size_vals)],
        }])
    created.append((tmpl_id, name, action))
    print('%-6s %s (id=%s)' % (action, name, tmpl_id))

# ---------- 4. 验证 ----------
prods = rpc('product.template', 'search_read', [[('name', 'like', '奥登科·')]],
            {'fields': ['name', 'list_price', 'is_published', 'website_url'], 'limit': 20})
print('\n=== 验证 (%d 款) ===' % len(prods))
for p in prods:
    print('%s ¥%s 发布:%s %s' % (p['name'], p['list_price'], p['is_published'], p.get('website_url')))

json.dump({'cat_ids': cat_ids,
           'products': [{'id': t, 'name': n} for t, n, a in created]},
          open('/workspace/outdoor_data.json', 'w'), ensure_ascii=False, indent=1)
print('\n数据已保存到 outdoor_data.json')
