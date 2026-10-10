#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包 odk_dispatch v20.0.2.0.1 修复版 + 生成服务器一键部署脚本"""
import base64
import io
import os
import tarfile

SRC = "/workspace/deploy_odoo/addons/odk_dispatch"
TGZ = "/workspace/odk_dispatch_v2fix.tar.gz"
SH = "/workspace/odk_dispatch_fix.sh"


def skip(tarinfo):
    name = os.path.basename(tarinfo.name)
    if name in ("__pycache__",) or name.endswith(".pyc"):
        return None
    return tarinfo


# 1) 打 tar.gz（顶层目录 odk_dispatch/）
with tarfile.open(TGZ, "w:gz") as tf:
    tf.add(SRC, arcname="odk_dispatch", filter=skip)
size = os.path.getsize(TGZ)
print("tar.gz: %.1f KB" % (size / 1024))

# 2) base64
b64 = base64.b64encode(open(TGZ, "rb").read()).decode()
print("base64: %.1f KB" % (len(b64) / 1024))

# 3) 生成一键部署脚本
script = """#!/bin/bash
# ============================================================
# 奥登科 ERP · odk_dispatch 现场派工+条码模块 修复部署脚本 v20.0.2.0.1
# 修复内容：移除 Odoo 20 已废弃的 report 依赖（该依赖导致模块被整体跳过）
# 用法：在服务器上任意目录执行:  bash odk_dispatch_fix.sh
# 动作：解出模块 → 替换 deploy_odoo/addons/odk_dispatch → 重启 Odoo 容器
# ============================================================
set -e
[ -d /www/wwwroot/deploy_odoo ] || { echo "!! 未找到 /www/wwwroot/deploy_odoo，请确认部署目录"; exit 1; }
cd /www/wwwroot
echo '== 还原修复版模块包 =='
echo '__B64__' | base64 -d > odk_dispatch_fix.tar.gz
tar zxf odk_dispatch_fix.tar.gz
echo '== 替换模块文件（先删旧目录，避免残留） =='
rm -rf deploy_odoo/addons/odk_dispatch
cp -r odk_dispatch deploy_odoo/addons/
rm -rf odk_dispatch odk_dispatch_fix.tar.gz
echo '== 校验 manifest 依赖（应输出 odk_wms mrp web，无 report） =='
grep -A1 '"depends"' deploy_odoo/addons/odk_dispatch/__manifest__.py || true
grep '"version"' deploy_odoo/addons/odk_dispatch/__manifest__.py
echo '== 重启 Odoo 容器（加载修复版模块） =='
cd deploy_odoo
docker compose restart odoo
echo '等待 Odoo 启动...'
for i in $(seq 1 30); do
  curl -s -o /dev/null http://127.0.0.1:8069/web/login && break
  sleep 2
done
code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 http://127.0.0.1:8069/web/login || true)
echo "Odoo HTTP: ${code:-无响应}"
if [ "$code" != "200" ]; then
  echo '!! 启动异常，查看日志：'
  docker compose logs --tail 60 odoo
  exit 1
fi
echo '============================================================'
echo ' 修复包部署完成，Odoo 已重启（HTTP '"$code"'）。'
echo ' 请回到对话窗口告知技术，远程完成模块升级与验证。'
echo '============================================================'
""".replace("__B64__", b64)

with open(SH, "w") as f:
    f.write(script)
os.chmod(SH, 0o755)
print("脚本: %s (%.1f KB)" % (SH, os.path.getsize(SH) / 1024))

# 4) 自检：还原脚本里的包并比对 manifest
import tempfile
sh_txt = open(SH).read()
b64_in = sh_txt.split("| base64 -d", 1)[0].rsplit("echo '", 1)[1]
raw = base64.b64decode(b64_in)
tf = tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz")
manifest = tf.extractfile("odk_dispatch/__manifest__.py").read().decode()
assert '"depends": ["odk_wms", "mrp", "web"]' in manifest, "manifest 依赖未修复!"
assert '"version": "20.0.2.0.2"' in manifest, "版本号未更新!"
assert '"report"' not in manifest, "report 依赖仍在!"
names = tf.getnames()
assert "odk_dispatch/report/barcode_report.xml" in names
assert not any(
    'report_file' in tf.extractfile(n).read().decode('utf-8', 'replace')
    for n in names if 'barcode_views' in n), "barcode_views.xml 仍含 report_file!"
print("自检 OK：包内 manifest 依赖=odk_wms/mrp/web，版本=20.0.2.0.2，文件数=%d" % len(names))
