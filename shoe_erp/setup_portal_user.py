# -*- coding: utf-8 -*-
"""上线安全收尾：创建低权限门户专用账号并生成 API 令牌。

背景：门户登录页原先自动填入 Administrator 管理员令牌（内嵌于公开页面，
任何访客一键即获全量权限）。本脚本改为创建专用低权限账号（仅门户
所需角色），生成的令牌将替换页面中的管理员令牌。

脚本本身在服务器侧运行，管理员令牌不出现在任何公开资源中。

用法：python3 setup_portal_user.py
      --verify-only  仅对已存在的门户账号重新做权限验证
"""
import json
import sys

import requests

BASE = "http://220.162.99.166:88"
ADMIN_TOKEN = "77455c7d4b3a8fe:f36c1a4b10e8b5e"
PORTAL_EMAIL = "portal@aodengke.com"
PORTAL_NAME = "门户专用账号"
# 门户最小角色集：库存(Stock Entry 扫描写入/Bin)、生产、采购、销售、财务(对账/GL)、委外
ROLE_CANDIDATES = ["Stock User", "Manufacturing User", "Purchase User",
                   "Sales User", "Accounts User", "Subcontracting User"]

# 门户页面实际访问的全部 doctype（读）
READ_DOCTYPES = [
    "Sales Order", "Work Order", "Material Request", "Purchase Order",
    "Subcontracting Order", "Stock Entry", "Job Card", "Production Plan",
    "Purchase Receipt", "Subcontracting Receipt", "Purchase Invoice",
    "Payment Entry", "Supplier", "Bin", "Item", "GL Entry", "Customer",
]

admin = requests.Session()
admin.headers.update({
    "Authorization": f"token {ADMIN_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
})


def log(msg, ok=True):
    print(("OK " if ok else "ERR") + " | " + msg)


def list_doctypes(token):
    """用指定令牌逐一探测门户所需 doctype 的读权限"""
    sess = requests.Session()
    sess.headers.update({"Authorization": f"token {token}", "Accept": "application/json"})
    fails = []
    for dt in READ_DOCTYPES:
        r = sess.get(f"{BASE}/api/resource/{dt}",
                     params={"limit_page_length": 1}, timeout=30)
        if r.status_code != 200:
            fails.append(f"{dt}: HTTP {r.status_code}")
    return fails


def main():
    verify_only = "--verify-only" in sys.argv

    # ---- 1) 角色存在性校验 ----
    r = admin.get(f"{BASE}/api/resource/Role",
                  params={"filters": json.dumps([["name", "in", ROLE_CANDIDATES]]),
                          "limit_page_length": 0, "fields": json.dumps(["name"])},
                  timeout=30)
    r.raise_for_status()
    have = {d["name"] for d in r.json()["data"]}
    roles = [x for x in ROLE_CANDIDATES if x in have]
    missing = [x for x in ROLE_CANDIDATES if x not in have]
    if missing:
        log(f"角色缺失（将跳过）: {missing}", ok=False)
    log(f"将赋予角色: {roles}")

    # ---- 2) 创建/复用门户用户 ----
    r = admin.get(f"{BASE}/api/resource/User",
                  params={"filters": json.dumps([["name", "=", PORTAL_EMAIL]]),
                          "limit_page_length": 1},
                  timeout=30)
    exists = bool(r.json().get("data"))
    if not exists and not verify_only:
        r = admin.post(f"{BASE}/api/resource/User", json={
            "email": PORTAL_EMAIL,
            "first_name": PORTAL_NAME,
            "enabled": 1,
            "send_welcome_email": 0,
            "user_type": "System User",
        }, timeout=60)
        if r.status_code not in (200, 201):
            log(f"创建用户失败: {r.status_code} {r.text[:300]}", ok=False)
            raise SystemExit(1)
        log(f"创建用户 {PORTAL_EMAIL}: HTTP {r.status_code}")
    elif exists:
        log(f"用户已存在: {PORTAL_EMAIL}")

    # ---- 3) 赋予角色 ----
    if not verify_only:
        r = admin.put(f"{BASE}/api/resource/User/{PORTAL_EMAIL}",
                      json={"roles": [{"role": x} for x in roles]}, timeout=60)
        if r.status_code != 200:
            log(f"赋予角色失败: {r.status_code} {r.text[:300]}", ok=False)
            raise SystemExit(1)
        log(f"赋予角色 {len(roles)} 个: HTTP {r.status_code}")

    # ---- 4) 生成 API 令牌 ----
    import os
    token = None
    if not verify_only:
        r = admin.post(f"{BASE}/api/method/frappe.core.doctype.user.user.generate_keys",
                       json={"user": PORTAL_EMAIL}, timeout=30)
        if r.status_code != 200:
            log(f"生成令牌失败: {r.status_code} {r.text[:300]}", ok=False)
            raise SystemExit(1)
        d = r.json()["message"]
        token = f"{d['api_key']}:{d['api_secret']}"
        log("已生成门户令牌")
    else:
        # 令牌经 PORTAL_TOKEN 环境变量传入，避免重复生成导致轮换
        token = os.environ.get("PORTAL_TOKEN")
        if not token:
            log("--verify-only 需通过环境变量 PORTAL_TOKEN 传入令牌", ok=False)
            raise SystemExit(1)

    if not token:
        raise SystemExit(1)

    # ---- 5) 门户令牌全量验证 ----
    p = requests.Session()
    p.headers.update({"Authorization": f"token {token}",
                      "Content-Type": "application/json", "Accept": "application/json"})

    r = p.get(f"{BASE}/api/method/frappe.auth.get_logged_user", timeout=30)
    log(f"身份验证: HTTP {r.status_code} → {r.json().get('message')}")
    assert r.json().get("message") == PORTAL_EMAIL, "身份不是门户账号！"

    fails = list_doctypes(token)
    if fails:
        log(f"读权限缺失: {fails}", ok=False)
    else:
        log(f"读权限验证通过（{len(READ_DOCTYPES)} 个 doctype 全部 200）")

    # 写权限：Stock Entry 草稿创建（创建后立即由管理员删除，不留痕迹）
    # 选用有库存的材料料件（有评估率），避免撞上业务校验而非权限问题
    r = admin.get(f"{BASE}/api/resource/Bin",
                  params={"filters": json.dumps([["actual_qty", ">", 0]]),
                          "fields": json.dumps(["item_code", "warehouse"]),
                          "limit_page_length": 1},
                  timeout=30)
    bins = r.json()["data"]
    item_code = bins[0]["item_code"] if bins else None
    if not item_code:
        log("无可 Stock Entry 测试的库存料件，跳过写权限验证", ok=False)
    else:
        src_wh = bins[0]["warehouse"]
        dst_wh = "半成品仓 - 奥登科" if src_wh != "半成品仓 - 奥登科" else "成品仓 - 奥登科"
        r = p.post(f"{BASE}/api/resource/Stock Entry", json={
            "stock_entry_type": "Material Transfer",
            "items": [{"item_code": item_code, "qty": 1,
                       "s_warehouse": src_wh, "t_warehouse": dst_wh}],
        }, timeout=60)
        if r.status_code in (200, 201):
            se = r.json()["data"]["name"]
            log(f"Stock Entry 写权限验证通过（草稿 {se} · {item_code}，即将删除）")
            admin.delete(f"{BASE}/api/resource/Stock Entry/{se}", timeout=30)
            log(f"测试草稿已删除: {se}")
        else:
            log(f"Stock Entry 写权限验证失败: {r.status_code} {r.text[:300]}", ok=False)

    # 越权负测试（写路径）：门户令牌不得创建/修改用户
    r = p.post(f"{BASE}/api/resource/User", json={
        "email": "evil@test.com", "first_name": "x", "send_welcome_email": 0}, timeout=30)
    log(f"负测试·创建用户（应 403/417）: HTTP {r.status_code}",
        ok=(r.status_code in (403, 404, 417)))
    r = p.put(f"{BASE}/api/resource/User/Administrator",
              json={"first_name": "x"}, timeout=30)
    log(f"负测试·修改 Administrator（应 403）: HTTP {r.status_code}",
        ok=(r.status_code in (403, 404)))

    # 越权负测试：门户令牌不得访问用户列表
    r = p.get(f"{BASE}/api/resource/User", params={"limit_page_length": 1}, timeout=30)
    log(f"越权负测试（User 列表应 403/404）: HTTP {r.status_code}",
        ok=(r.status_code in (403, 404)))

    print("\nPORTAL_TOKEN=" + token)


if __name__ == "__main__":
    main()
