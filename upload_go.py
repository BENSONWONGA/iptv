# -*- coding: utf-8 -*-
"""上传 go.sh 引导脚本（终端里只需一行短命令）"""
import requests

BASE = "http://220.162.99.166:88"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"
s = requests.Session()
s.headers.update({"Authorization": f"token {TOKEN}"})

GO_SH = """#!/bin/bash
# 奥登科 ERP 一键引导：下载 Odoo 部署包并安装
cd /www/wwwroot || { echo "目录不存在"; exit 1; }
echo "== 下载部署包 =="
wget -q http://127.0.0.1:88/files/odk_odoo_deploy_v2.tar.gz || { echo "下载失败"; exit 1; }
tar zxf odk_odoo_deploy_v2.tar.gz || { echo "解压失败"; exit 1; }
bash deploy_odoo/install.sh
"""

with open("/tmp/go.sh", "w") as f:
    f.write(GO_SH)

with open("/tmp/go.sh", "rb") as f:
    r = s.post(
        f"{BASE}/api/method/upload_file",
        files={"file": ("go.sh", f, "text/x-shellscript")},
        data={"folder": "Home", "is_private": 0, "file_name": "go.sh"},
        timeout=60,
    )
msg = r.json().get("message") or {}
print("上传:", r.status_code, msg.get("file_url"))

r = requests.get(f"{BASE}{msg.get('file_url')}", timeout=30)
print("验证:", r.status_code, len(r.content), "字节")
print(r.text[:120])
