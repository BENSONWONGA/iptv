# -*- coding: utf-8 -*-
"""部署 UI 为 Frappe Web Page（路由 /odk，同域免 CORS）"""
import json
import os
import requests

BASE = "http://220.162.99.166:88"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"
HERE = os.path.dirname(os.path.abspath(__file__))

session = requests.Session()
session.headers.update({
    "Authorization": f"token {TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
})


def log(msg, ok=True):
    print(("OK " if ok else "ERR") + " | " + msg)


content = open(os.path.join(HERE, "odk_webpage.html"), encoding="utf-8").read()
data = {
    "doctype": "Web Page",
    "title": "鞋业智造门户",
    "route": "odk",
    "content_type": "HTML",
    "main_section_html": content,
    "show_title": 0,
    "full_width": 1,
    "published": 1,
    "text_align": "Left",
}

# 已存在则更新，否则创建
existing = session.get(
    f"{BASE}/api/resource/Web Page",
    params={"filters": json.dumps([["route", "=", "odk"]]), "limit_page_length": 1},
    timeout=30,
).json().get("data", [])
if existing:
    name = existing[0]["name"]
    r = session.put(f"{BASE}/api/resource/Web%20Page/{name}", json=data, timeout=120)
    log(f"更新 Web Page {name}: HTTP {r.status_code}")
else:
    r = session.post(f"{BASE}/api/resource/Web%20Page", json=data, timeout=120)
    name = r.json().get("data", {}).get("name")
    log(f"创建 Web Page {name}: HTTP {r.status_code}")

if r.status_code not in (200, 201):
    log(f"失败详情: {r.text[:400]}", False)
    raise SystemExit(1)

# 验证匿名访问
r2 = requests.get(f"{BASE}/odk", timeout=60)
ok = (r2.status_code == 200
      and "奥登科" in r2.content.decode("utf-8", "ignore")
      and "Content-Disposition" not in r2.headers.get("Content-Disposition", ""))
ctype = r2.headers.get("Content-Type", "")
log(f"访问 /odk: HTTP {r2.status_code} | {ctype} | {len(r2.content) / 1024:.1f} KB | "
    f"CD={r2.headers.get('Content-Disposition') or '无(inline)'}")
log("部署成功: http://220.162.99.166:88/odk" if ok else "访问异常，请检查", ok)
