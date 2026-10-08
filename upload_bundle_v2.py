# -*- coding: utf-8 -*-
"""上传 v2 部署包（自动删除旧版，避免副本混淆）"""
import json
import requests

BASE = "http://220.162.99.166:88"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"
SRC = "/workspace/odk_odoo_deploy_v2.tar.gz"

s = requests.Session()
s.headers.update({"Authorization": f"token {TOKEN}", "Accept": "application/json"})


def log(msg, ok=True):
    print(("OK " if ok else "ERR") + " | " + msg)


# 1) 找到并删除旧部署包（v1 与同名文件）
for r in s.get(f"{BASE}/api/resource/File",
               params={"filters": json.dumps([["file_url", "like", "%odk_odoo_deploy%"]]),
                       "limit_page_length": 0}, timeout=30).json().get("data", []):
    name = r.get("name")
    rr = s.post(f"{BASE}/api/method/frappe.client.delete",
                json={"doctype": "File", "name": name}, timeout=60)
    log(f"删除旧包 {name}: HTTP {rr.status_code}")

# 2) 上传 v2
with open(SRC, "rb") as f:
    r = s.post(
        f"{BASE}/api/method/upload_file",
        files={"file": ("odk_odoo_deploy_v2.tar.gz", f, "application/gzip")},
        data={"folder": "Home", "is_private": 0, "file_name": "odk_odoo_deploy_v2.tar.gz"},
        timeout=120,
    )
msg = r.json().get("message") or {}
url = msg.get("file_url")
log(f"上传: HTTP {r.status_code} url={url}")
if not url:
    log(f"上传返回异常: {str(r.json())[:300]}", False)
    raise SystemExit(1)

# 3) 验证外网可下载
r = requests.get(f"{BASE}{url}", timeout=30)
log(f"外网验证: HTTP {r.status_code} | {len(r.content)/1024:.1f} KB")
ok = r.status_code == 200 and len(r.content) > 10000
log("v2 部署包就绪: " + url, ok)
