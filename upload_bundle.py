# -*- coding: utf-8 -*-
"""把 Odoo 部署包上传到线上站点（Frappe 上传为公开文件，供服务器 wget）"""
import json
import requests

BASE = "http://220.162.99.166:88"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"
SRC = "/workspace/odk_odoo_deploy.tar.gz"

session = requests.Session()
session.headers.update({"Authorization": f"token {TOKEN}"})


def log(msg, ok=True):
    print(("OK " if ok else "ERR") + " | " + msg)


# 1) 删除旧版本，避免生成副本文件
try:
    r = session.post(f"{BASE}/api/method/frappe.client.delete",
                    json={"doctype": "File", "name": "Home/odk_odoo_deploy.tar.gz"}, timeout=60)
    log(f"删除旧包: HTTP {r.status_code}")
except Exception as e:
    log(f"删除旧包（忽略）: {e}")

# 2) 上传新版本
with open(SRC, "rb") as f:
    r = session.post(
        f"{BASE}/api/method/upload_file",
        files={"file": ("odk_odoo_deploy.tar.gz", f, "application/gzip")},
        data={"folder": "Home", "is_private": 0, "file_name": "odk_odoo_deploy.tar.gz"},
        timeout=120,
    )
msg = r.json().get("message") or {}
log(f"上传: HTTP {r.status_code} name={msg.get('name')} url={msg.get('file_url')}")
if not msg.get("file_url"):
    log(f"上传返回异常: {str(r.json())[:400]}", False)
    raise SystemExit(1)

# 3) 验证外网可下载
r = requests.get(f"{BASE}{msg['file_url']}", timeout=30)
ctype = r.headers.get("Content-Type", "")
log(f"外网验证 {msg['file_url']}: HTTP {r.status_code} | {ctype} | {len(r.content)/1024:.1f} KB")
json.dump({"file": msg.get("name"), "url": msg.get("file_url")},
          open("/workspace/shoe_erp/bundle_deploy_state.json", "w"), ensure_ascii=False, indent=1)
ok = r.status_code == 200 and len(r.content) > 10000
log("部署包上传成功" if ok else "外网验证异常", ok)
