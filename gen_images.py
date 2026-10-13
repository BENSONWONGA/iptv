#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成户外鞋网站图片素材（主视觉/产品图/品牌图）"""
import os
import urllib.parse
import concurrent.futures as cf

import requests

API = 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image'
OUT = '/workspace/site_assets'
os.makedirs(OUT, exist_ok=True)

# (文件名, 提示词, 尺寸)
IMAGES = [
    # 主视觉
    ('hero_mountain', 'Cinematic wide photograph of hikers walking along a rocky mountain ridge at golden sunrise, dramatic peaks and sea of clouds in background, epic outdoor adventure landscape photography, warm orange light, high resolution', 'landscape_16_9'),
    # 品牌故事
    ('brand_story', 'Modern professional shoe manufacturing workshop, craftsman handcrafting brown leather hiking boots on workbench, warm ambient lighting, precision craftsmanship, shallow depth of field, photorealistic', 'landscape_4_3'),
    # 12 款产品图（白底电商风格）
    ('p01_zhengtu', 'Professional e-commerce product photography of a brown and orange mid-cut waterproof hiking boot with rugged rubber outsole, side profile view centered on clean light gray studio background, high detail, sharp focus, photorealistic', 'square'),
    ('p02_lanfeng', 'Professional e-commerce product photography of a grey and green low-cut lightweight hiking shoe with breathable mesh upper, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p03_lieying', 'Professional e-commerce product photography of a bright orange and red aggressive trail running shoe with deep lugs, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p04_yunchi', 'Professional e-commerce product photography of a blue and teal cushioned trail running shoe with thick white foam midsole, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p05_dianfeng', 'Professional e-commerce product photography of a yellow and black technical mountaineering double boot with crampon-compatible rigid sole, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p06_suxi', 'Professional e-commerce product photography of a grey and aqua water shoe with drainage holes and quick-dry mesh, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p07_shamo', 'Professional e-commerce product photography of a sand tan suede desert hiking boot with crepe sole, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p08_jidi', 'Professional e-commerce product photography of a white and grey insulated winter mountaineering boot with integrated gaiter, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p09_qingye', 'Professional e-commerce product photography of a dark grey and brown casual outdoor walking shoe, minimalist design, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p10_jifeng', 'Professional e-commerce product photography of a white and red carbon plate racing trail running shoe, sleek aerodynamic design, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p11_tietu', 'Professional e-commerce product photography of a full grain dark brown leather heavy duty backpacking boot with red laces, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
    ('p12_yanque', 'Professional e-commerce product photography of a black and orange climbing approach shoe with sticky rubber sole, side profile view centered on clean light gray studio background, high detail, photorealistic', 'square'),
]


def fetch(item):
    name, prompt, size = item
    path = os.path.join(OUT, name + '.jpg')
    if os.path.exists(path) and os.path.getsize(path) > 20000:
        return name, 'skip'
    url = API + '?prompt=' + urllib.parse.quote(prompt) + '&image_size=' + size
    try:
        r = requests.get(url, timeout=300)
        if r.status_code == 200 and len(r.content) > 20000 and r.headers.get('content-type', '').startswith('image'):
            with open(path, 'wb') as f:
                f.write(r.content)
            return name, 'ok %dKB' % (len(r.content) // 1024)
        return name, 'FAIL %s %s' % (r.status_code, r.headers.get('content-type'))
    except Exception as e:
        return name, 'ERR %s' % e


with cf.ThreadPoolExecutor(6) as tp:
    for name, status in tp.map(fetch, IMAGES):
        print('%-16s %s' % (name, status))

print('--- 完成 ---')
for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)) // 1024, 'KB')
