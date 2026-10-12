#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 256 画布 favicon 源 PNG（供服务器端 image_process 转 ICO）"""
from PIL import Image

img = Image.open('/workspace/.uploads/31c555f2-339a-4f75-b82b-03028e55105b_奥登科logops.png').convert('RGBA')
trimmed = img.crop(img.getbbox())
w, h = trimmed.size
canvas = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
scale = min(256 / w, 256 / h)
nw, nh = int(w * scale), int(h * scale)
resized = trimmed.resize((nw, nh), Image.LANCZOS)
canvas.paste(resized, ((256 - nw) // 2, (256 - nh) // 2), resized)
canvas.save('/tmp/adk_fav.png', format='PNG', optimize=True)
import os
print('生成 /tmp/adk_fav.png', os.path.getsize('/tmp/adk_fav.png'), 'bytes')
