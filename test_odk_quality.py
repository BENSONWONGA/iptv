# -*- coding: utf-8 -*-
"""odk_quality 端到端测试：来料抽检 → 部分合格判定 → 超量约束 →
生成异常单 → 异常单闭环（待处理→处理中→关闭）→ 异常分支"""
import xmlrpc.client

URL = "http://127.0.0.1:8069"
DB = "odoo20"
USER = "admin"
PWD = "admin"

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PWD, {})
assert uid, "admin 登录失败"
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
R = []


def call(model, method, *args, **kw):
    return models.execute_kw(DB, uid, PWD, model, method, list(args), kw)


def check(name, ok, detail=""):
    R.append(ok)
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else "  --> " + str(detail)[:200]))


# ── 1) 来料抽检：抽 50，合格 46，不合格 4 ────────────────────
p_fab = call("product.product", "search", [("default_code", "=", "M-FAB-001")], limit=1)
check("测试物料存在", bool(p_fab))
p_vendor = call("res.partner", "search", [("name", "=", "宏达针车厂")], limit=1)

qc_id = call("odk.quality.check", "create", {
    "check_type": "iqc", "product_id": p_fab[0],
    "product_qty": 50.0, "qty_passed": 46.0, "qty_failed": 4.0,
    "partner_id": p_vendor[0] if p_vendor else False,
    "note": "抽检50码：4码同面差色超标准",
})
qc = call("odk.quality.check", "read", [qc_id], ["name", "result"])[0]
check("质检单创建并取号 QC", qc["name"].startswith("QC/"), qc["name"])
check("46/4 → 部分合格", qc["result"] == "partial", qc["result"])

# 全合格 → pass
qc2 = call("odk.quality.check", "create", {
    "check_type": "fqc", "product_id": p_fab[0],
    "product_qty": 30.0, "qty_passed": 30.0, "qty_failed": 0.0})
check("30/0 → 合格", call("odk.quality.check", "read", [qc2], ["result"])[0]["result"] == "pass")

# 全不合格 → fail
qc3 = call("odk.quality.check", "create", {
    "check_type": "fqc", "product_id": p_fab[0],
    "product_qty": 10.0, "qty_passed": 0.0, "qty_failed": 10.0})
check("0/10 → 不合格", call("odk.quality.check", "read", [qc3], ["result"])[0]["result"] == "fail")

# ── 2) 约束：合格+不合格 > 抽检数 → 拒绝 ────────────────────
try:
    call("odk.quality.check", "create", {
        "check_type": "iqc", "product_id": p_fab[0],
        "product_qty": 10.0, "qty_passed": 8.0, "qty_failed": 5.0})
    check("超抽检数被拒绝", False, "未抛错")
except Exception as e:
    check("超抽检数被拒绝", "超过抽检数量" in str(e), str(e)[:80])

# ── 3) 不合格 → 一键生成异常单 ──────────────────────────────
res = call("odk.quality.check", "action_create_alert", [qc_id])
alert_id = res.get("res_id")
check("生成异常单并跳转", bool(alert_id), res)
alert = call("odk.quality.alert", "read", [alert_id],
             ["name", "state", "alert_type", "qty_bad", "product_id", "partner_id", "check_id"])[0]
check("异常单取号 QA", alert["name"].startswith("QA/"), alert["name"])
check("异常单带出：不良数4 / 类型来料 / 来源质检单",
      alert["qty_bad"] == 4.0 and alert["alert_type"] == "iqc" and alert["check_id"][0] == qc_id,
      alert)
check("异常单初始状态 待处理", alert["state"] == "open", alert["state"])

# 合格单生成异常被拒
try:
    call("odk.quality.check", "action_create_alert", [qc2])
    check("合格单生成异常被拒绝", False, "未抛错")
except Exception as e:
    check("合格单生成异常被拒绝", "没有不合格数量" in str(e), str(e)[:80])

# ── 4) 异常单闭环：待处理 → 处理中 → 关闭（需措施） ──────────
call("odk.quality.alert", "action_open", [alert_id])
check("开始处理 → 处理中", call("odk.quality.alert", "read", [alert_id], ["state"])[0]["state"] == "in_progress")
try:
    call("odk.quality.alert", "action_close", [alert_id])
    check("无措施关闭被拒绝", False, "未抛错")
except Exception as e:
    check("无措施关闭被拒绝", "处理措施" in str(e), str(e)[:80])
call("odk.quality.alert", "write", [alert_id], {"solution": "4码退回厂家换料，供应商承担运费"})
call("odk.quality.alert", "action_close", [alert_id])
check("填写措施后关闭成功", call("odk.quality.alert", "read", [alert_id], ["state"])[0]["state"] == "done")

# 质检单关联异常计数
qc = call("odk.quality.check", "read", [qc_id], ["alert_count"])[0]
check("质检单异常计数 = 1", qc["alert_count"] == 1, qc)

print(f"\n========== odk_quality 测试: {sum(R)}/{len(R)} PASS ==========")
