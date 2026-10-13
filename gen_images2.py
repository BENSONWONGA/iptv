#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新拉取图片：API 为异步生成，需刷新获取真实图片"""
import os
import time
import urllib.parse

import requests

API = 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image'
OUT = '/workspace/site_assets'

NAMES = ['hero_mountain', 'brand_story'] + [
    'p01_zhengtu', 'p02_lanfeng', 'p03_lieying', 'p04_yunchi',
    'p05_dianfeng', 'p06_suxi', 'p07_shamo', 'p08_jidi',
    'p09_qingye', 'p10_jifeng', 'p11_tietu', 'p12_yanque']

PROMPTS = {
    'hero_mountain': 'Cinematic wide photograph of hikers walking along a rocky mountain ridge at golden sunrise, dramatic peaks and sea of clouds in background, epic outdoor adventure landscape photography, warm orange light, high resolution',
    'brand_story': 'Modern professional shoe manufacturing workshop, craftsman handcrafting brown leather hiking boots on workbench, warm ambient lighting, precision craftsmanship, shallow depth of field, photorealistic',
    'p01_zhengtu': 'Professional e-commerce product photography of a brown and orange mid-cut waterproof hiking boot with rugged rubber outsole, side profile view centered on clean light gray studio background, high detail, sharp focus, photorealistic',
    'p02_lanfeng': 'Professional e-commerce product photography of a grey and green low-cut lightweight hiking shoe with breathable mesh upper, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p03_lieying': 'Professional e-commerce product photography of a bright orange and red aggressive trail running shoe with deep lugs, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p04_yunchi': 'Professional e-commerce product photography of a blue and teal cushioned trail running shoe with thick white foam midsole, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p05_dianfeng': 'Professional e-commerce product photography of a yellow and black technical mountaineering double boot with crampon-compatible rigid sole, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p06_suxi': 'Professional e-commerce product photography of a grey and aqua water shoe with drainage holes and quick-dry mesh, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p07_shamo': 'Professional e-commerce product photography of a sand tan suede desert hiking boot with crepe sole, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p08_jidi': 'Professional e-commerce product photography of a white and grey insulated winter mountaineering boot with integrated gaiter, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p09_qingye': 'Professional e-commerce product photography of a dark grey and brown casual outdoor walking shoe, minimalist design, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p10_jifeng': 'Professional e-commerce product photography of a white and red carbon plate racing trail running shoe, sleek aerodynamic design, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p11_tietu': 'Professional e-commerce product photography of a full grain dark brown leather heavy duty backpacking boot with red laces, side profile view centered on clean light gray studio background, high detail, photorealistic',
    'p12_yanque': 'Professional e-commerce product photography of a black and orange climbing approach shoe with sticky rubber sole, side profile view centered on clean light gray studio background, high detail, photorealistic',
}
SIZES = {'hero_mountain': 'landscape_16_9', 'brand_story': 'landscape_4_3'}


def url_for(name):
    size = SIZES.get(name, 'square')
    return API + '?prompt=' + urllib.parse.quote(PROMPTS[name]) + '&image_size=' + size


def is_placeholder(content):
    # 占位图约 172KB 且内容固定；生成的 jpg 大小会不同
    return len(content) < 30000 or b'generating' in content[:2000]


s = requests.Session()
for name in NAMES:
    path = os.path.join(OUT, name + '.jpg')
    url = url_for(name)
    ok = False
    for attempt in range(8):
        try:
            r = s.get(url, timeout=300)
            c = r.content
            if r.status_code == 200 and len(c) > 30000 and not is_placeholder(c):
                # 与上次占位不同即可信
                with open(path, 'wb') as f:
                    f.write(c)
                print('%-16s ok %dKB (第%d次)' % (name, len(c) // 1024, attempt + 1))
                ok = True
                break
        except Exception as e:
            print('%-16s err %s' % (name, e))
        time.sleep(12)
    if not ok:
        print('%-16s FAILED' % name)

print('--- 最终结果 ---')
for f in sorted(os.listdir(OUT)):
    print(f, os.path.getsize(os.path.join(OUT, f)) // 1024, 'KB')
