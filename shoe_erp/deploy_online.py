# -*- coding: utf-8 -*-
"""部署 UI 到线上 ERPNext（发布为站点公开文件 /files/odk.html）"""
import json
import os
import requests

BASE = "http://220.162.99.166:88"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"  # 已轮换；此 /files/ 部署路径已弃用，改用 deploy_webpage.py（/odk）
HERE = os.path.dirname(os.path.abspath(__file__))
ODK = os.path.join(HERE, "odk.html")

session = requests.Session()
session.headers.update({"Authorization": f"token {TOKEN}"})


def log(msg, ok=True):
    print(("OK " if ok else "ERR") + " | " + msg)


# 1. 删除旧版本 File（避免生成 odk-1.html 之类副本）
try:
    r = session.post(f"{BASE}/api/method/frappe.client.delete",
                     json={"doctype": "File", "name": "Home/odk.html"}, timeout=60)
    log(f"删除旧 odk.html: HTTP {r.status_code}")
except Exception as e:
    log(f"删除旧文件（忽略）: {e}")

# 2. 上传新版本（公开文件 → URL /files/odk.html）
with open(ODK, "rb") as f:
    r = session.post(
        f"{BASE}/api/method/upload_file",
        files={"file": ("odk.html", f, "text/html")},
        data={"folder": "Home", "is_private": 0, "file_name": "odk.html"},
        timeout=120,
    )
try:
    j = r.json()
    msg = j.get("message") or j
    if isinstance(msg, dict):
        log(f"上传成功: name={msg.get('name')} file_url={msg.get('file_url')} "
            f"is_private={msg.get('is_private')}")
        STATE_FILE = os.path.join(HERE, "deploy_state.json")
        json.dump({"file": msg.get("name"), "url": msg.get("file_url")},
                  open(STATE_FILE, "w"), ensure_ascii=False, indent=1)
    else:
        log(f"上传返回: {str(msg)[:400]}")
except Exception as e:
    log(f"上传失败: HTTP {r.status_code} {r.text[:400]}", False)
    raise SystemExit(1)

# 3. 验证外网访问
r = requests.get(f"{BASE}/files/odk.html", timeout=30)
ctype = r.headers.get("Content-Type", "")
log(f"外网验证 /files/odk.html: HTTP {r.status_code} | {ctype} | {len(r.text) / 1024:.1f} KB")
if r.status_code == 200 and "html" in ctype and "奥登科" in r.text:
    log("部署成功: http://220.162.99.166:88/files/odk.html")
else:
    log("外网验证异常，请检查", False)
