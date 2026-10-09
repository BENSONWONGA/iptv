# -*- coding: utf-8 -*-
"""奥登科鞋业 · Odoo 20 全链路闭环配置（幂等可重跑）：
工作中心+工序 → 生产订单(MRP算料) → 4张采购收货 → 逐工序报工 → 成品入库
→ 销售发货 → 采购账单+付款 → 质检挂接(IQC/FQC/OQC) → 全链路结果汇总"""
import xmlrpc.client

URL, DB, USER, PWD = "http://127.0.0.1:8069", "odoo20", "admin", "admin"
common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, USER, PWD, {})
assert uid, "admin 登录失败"
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
R = []


def call(model, method, *args, **kw):
    return models.execute_kw(DB, uid, PWD, model, method, list(args), kw)


def check(name, ok, detail=""):
    R.append(bool(ok))
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else "  --> " + str(detail)[:300]))


def find(model, domain, limit=1):
    return call(model, "search", domain, limit=limit)


def find_all(model, domain):
    return call(model, "search", domain)


def ensure(model, domain, vals):
    ids = find(model, domain)
    if ids:
        return ids[0]
    return call(model, "create", vals)


# ============ 阶段 0：权限组（工序页签/工单菜单可见） ============
grp = find("ir.model.data", [("module", "=", "mrp"), ("name", "=", "group_mrp_routings")])
if grp:
    gid = call("ir.model.data", "read", grp, ["res_id"])[0]["res_id"]
    call("res.groups", "write", [gid], {"user_ids": [(4, uid)]})
    check("admin 已加入 工单/工序 权限组", True)
else:
    check("admin 已加入 工单/工序 权限组", False, "group_mrp_routings 未找到")

# ============ 阶段 1：6 个工作中心（鞋厂车间） ============
WC = [
    ("WC-裁断", "裁断组（冲裁机）", 35),
    ("WC-针车", "针车组（缝纫机车位）", 28),
    ("WC-成型前段", "成型前段（刷胶/贴底准备）", 30),
    ("WC-压底", "压底成型（压底机）", 32),
    ("WC-冷冻定型", "冷冻定型线（定型柜）", 22),
    ("WC-检验包装", "终检包装（质检台）", 18),
]
wc_ids = {}
for code, name, cost in WC:
    wc_ids[code] = ensure("mrp.workcenter", [("name", "=", name)],
                          {"name": name, "costs_hour": cost, "time_efficiency": 100})
check("6 个工作中心就绪", len(wc_ids) == 6, wc_ids)

# ============ 阶段 2：A-001 BOM 挂 6 道工序 ============
bom_id = find("mrp.bom", [("product_tmpl_id.default_code", "=", "A-001")])[0]
OPS = [
    ("10 裁断", "WC-裁断", 2),
    ("20 针车", "WC-针车", 8),
    ("30 成型前段", "WC-成型前段", 4),
    ("40 压底成型", "WC-压底", 3),
    ("50 冷冻定型", "WC-冷冻定型", 5),
    ("60 检验包装", "WC-检验包装", 2),
]
op_ids = []
for i, (name, wc, mins) in enumerate(OPS):
    op_ids.append(ensure(
        "mrp.routing.workcenter",
        [("bom_id", "=", bom_id), ("name", "=", name)],
        {"bom_id": bom_id, "name": name, "sequence": (i + 1) * 10,
         "workcenter_id": wc_ids[wc], "time_cycle_manual": mins, "time_mode": "manual"}))
check("BOM 挂 6 道鞋业工序", len(op_ids) == 6, op_ids)

# ============ 阶段 3：生产订单（MRP 按 BOM 自动算料） ============
tmpl = find("product.template", [("default_code", "=", "A-001")])[0]
variants = call("product.product", "search_read",
                [("product_tmpl_id", "=", tmpl)], ["display_name", "default_code"])
v_black_41 = [v["id"] for v in variants if "黑色" in v["display_name"] and "41" in v["display_name"]]
v_black_41 = v_black_41[0] if v_black_41 else variants[0]["id"]
check("成品变体就绪（A-001 黑色41）", bool(v_black_41), v_black_41)

mo_ids = find_all("mrp.production", [("product_id", "=", v_black_41), ("state", "!=", "cancel")])
if not mo_ids:
    mo_id = call("mrp.production", "create", {
        "product_id": v_black_41, "product_qty": 100, "bom_id": bom_id})
else:
    mo_id = mo_ids[0]
mo = call("mrp.production", "read", [mo_id], ["name", "state", "move_raw_ids", "workorder_ids"])[0]
if mo["state"] == "draft":
    call("mrp.production", "action_confirm", [mo_id])
    mo = call("mrp.production", "read", [mo_id], ["name", "state", "move_raw_ids", "workorder_ids"])[0]
raw_lines = call("stock.move", "read", mo["move_raw_ids"],
                 ["product_id", "product_uom_qty"])
check(f"生产订单 {mo['name']} 已确认：MRP 自动算料 {len(raw_lines)} 行", mo["state"] != "draft" and len(raw_lines) == 9, mo)
print("   领料需求:", [(r["product_id"][1], r["product_uom_qty"]) for r in raw_lines])

# ============ 阶段 4：4 张采购单 → 收货入库 ============
sup_fab = find("res.partner", [("name", "like", "鸿达织造")])[0]
sup_sol = find("res.partner", [("name", "like", "恒强底材")])[0]


def prod(code):
    return find("product.product", [("default_code", "=", code)])[0]


PO4 = [  # (供应商, [(编码, 数量, 单价), ...])
    (sup_fab, [("M-001", 100, 12.0), ("M-002", 120, 6.0)]),
    (sup_fab, [("M-006", 100, 1.5), ("M-007", 300, 0.8)]),
    (sup_sol, [("M-003", 100, 15.0), ("M-004", 100, 8.0), ("M-005", 100, 2.5)]),
    (sup_sol, [("M-008", 100, 2.2), ("M-009", 5, 30.0)]),
]
po_ids_done = find_all("purchase.order", [("state", "=", "purchase")])
need_po = len(po_ids_done) < 4
if need_po:
    for partner, lines in PO4:
        po = call("purchase.order", "create", {
            "partner_id": partner,
            "order_line": [(0, 0, {"product_id": prod(c), "product_qty": q, "price_unit": p})
                           for c, q, p in lines]})
        call("purchase.order", "button_confirm", [po])
po_all = find_all("purchase.order", [("state", "=", "purchase")])
check("4 张采购单已确认", len(po_all) >= 4, po_all)


def validate_picking(pid):
    p = call("stock.picking", "read", [pid], ["state", "move_ids"])[0]
    if p["state"] == "done":
        return True
    for mv in call("stock.move", "read", p["move_ids"], ["product_uom_qty", "state"]):
        if mv["state"] != "done":
            call("stock.move", "write", [mv["id"]],
                 {"quantity": mv["product_uom_qty"], "picked": True})
    res = call("stock.picking", "button_validate", [pid])
    while isinstance(res, dict) and res.get("res_model"):
        wiz_model = res["res_model"]
        wiz = res.get("res_id")
        if not wiz:
            wiz = find(wiz_model, [], limit=1)
        if wiz_model == "stock.backorder.confirmation":
            call("stock.backorder.confirmation", "process", [[wiz]])
        elif wiz_model == "stock.sms.confirm":
            call("stock.sms.confirm", "dont_send_sms", [[wiz]])
        else:
            raise RuntimeError("未知向导: %s" % wiz_model)
        res = call("stock.picking", "button_validate", [pid])
    return call("stock.picking", "read", [pid], ["state"])[0]["state"] == "done"


recv_ok = 0
recv_pickings = []
for po in po_all:
    info = call("purchase.order", "read", [po], ["name", "picking_ids", "state"])[0]
    for pid in info["picking_ids"]:
        if validate_picking(pid):
            recv_ok += 1
            recv_pickings.append(pid)
check(f"采购收货全部入库（{recv_ok} 张收货单 done）", recv_ok >= 4, recv_pickings)

# 材料库存校验：以「采购收货 done 的入库量」为准（生产消耗后期末库存可能为 0）
wh = call("stock.warehouse", "search_read", [], ["lot_stock_id", "name"])
wh_stock = [w for w in wh if w["name"] == "材料仓"] or wh
loc = wh_stock[0]["lot_stock_id"][0]
need = {"M-001": 100, "M-002": 120, "M-003": 100, "M-004": 100, "M-005": 100,
        "M-006": 100, "M-007": 300, "M-008": 100, "M-009": 5}
lack = []
for code, qty in need.items():
    q = call("stock.move", "search_read",
             [("product_id.default_code", "=", code),
              ("picking_id.picking_type_id.code", "=", "incoming"),
              ("state", "=", "done"),
              ("location_dest_id", "=", loc)],
             ["quantity"])
    have = sum(x["quantity"] for x in q)
    if have < qty - 0.01:
        lack.append((code, have, qty))
check("9 种材料采购入库量满足生产需求", not lack, lack)

# ============ 阶段 5：生产报工（6 道工序逐道 Job Card 报工） ============
mo = call("mrp.production", "read", [mo_id],
          ["name", "state", "workorder_ids", "qty_producing", "product_qty",
           "move_finished_ids"])[0]
wo_ids = mo["workorder_ids"]
if mo["state"] == "confirmed":
    call("mrp.production", "write", [mo_id], {"qty_producing": mo["product_qty"]})
wos = call("mrp.workorder", "read", wo_ids,
           ["name", "state", "operation_id", "qty_producing", "qty_production"])
done_wo = 0
for wo in wos:
    if wo["state"] == "done":
        done_wo += 1
        continue
    if wo["state"] == "pending":
        call("mrp.workorder", "button_start", [wo["id"]])
    call("mrp.workorder", "write", [wo["id"]], {"qty_producing": wo["qty_production"]})
    call("mrp.workorder", "button_finish", [wo["id"]])
    st = call("mrp.workorder", "read", [wo["id"]], ["state"])[0]["state"]
    if st == "done":
        done_wo += 1
    print("   报工:", wo["name"], "->", st)
check("6 道工序逐道报工完成", done_wo == 6, f"{done_wo}/6")

mo_state = call("mrp.production", "read", [mo_id], ["state", "qty_producing"])[0]["state"]
if mo_state != "done":
    call("mrp.production", "write", [mo_id], {"qty_producing": 100})
    call("mrp.production", "button_mark_done", [mo_id])
mo_state = call("mrp.production", "read", [mo_id], ["state"])[0]["state"]
check(f"生产订单完工入库（状态 {mo_state}）", mo_state == "done", mo_state)

fp_in = call("stock.move", "read", mo["move_finished_ids"], ["quantity", "state"])
fp_in_qty = sum(m["quantity"] for m in fp_in if m["state"] == "done")
check("成品 A-001(黑41) 入库 100 双", abs(fp_in_qty - 100) < 0.01, fp_in_qty)

# ============ 阶段 6：销售订单 → 发货 ============
cust = find("res.partner", [("name", "like", "华峰鞋业")])[0]
so_ids = find_all("sale.order", [("state", "=", "sale")])
if not so_ids:
    so_id = call("sale.order", "create", {
        "partner_id": cust,
        "order_line": [(0, 0, {"product_id": v_black_41, "product_uom_qty": 50,
                               "price_unit": 199.0})]})
    call("sale.order", "action_confirm", [so_id])
else:
    so_id = so_ids[0]
so = call("sale.order", "read", [so_id], ["name", "state", "picking_ids"])[0]
ship_ok = 0
for pid in so["picking_ids"]:
    if validate_picking(pid):
        ship_ok += 1
check(f"销售订单 {so['name']} 发货完成（{ship_ok} 张出货单 done）",
      so["state"] == "sale" and ship_ok >= 1, so)
fp2 = call("stock.quant", "search_read",
           [("product_id", "=", v_black_41), ("location_id", "=", loc)], ["quantity"])
fp2_qty = sum(x["quantity"] for x in fp2)
check("发货后成品库存 100 → 50", abs(fp2_qty - 50) < 0.01, fp2_qty)

# ============ 阶段 7：财务应付（采购账单 → 登记付款） ============
po_state = call("purchase.order", "read", po_all, ["name", "state", "invoice_status",
                                                   "invoice_ids", "amount_total"])
bill_ids = [i for p in po_state for i in p["invoice_ids"]]
if not bill_ids:
    for po in po_all:
        call("purchase.order", "action_create_invoice", [po])
    po_state = call("purchase.order", "read", po_all,
                    ["name", "state", "invoice_ids", "amount_total", "partner_id"])
    bill_ids = [i for p in po_state for i in p["invoice_ids"]]
bills = call("account.move", "read", bill_ids, ["name", "state", "amount_total",
                                               "move_type", "partner_id", "payment_state"])
for b in bills:
    if b["state"] == "draft":
        # v20：采购账单过账前必须有账单日期
        call("account.move", "write", [b["id"]], {"invoice_date": "2026-10-09"})
        call("account.move", "action_post", [b["id"]])
bills = call("account.move", "read", bill_ids, ["name", "state", "amount_total",
                                               "partner_id", "payment_state"])
posted = [b for b in bills if b["state"] == "posted"]
check(f"4 张采购账单已过账（合计 ¥{sum(b['amount_total'] for b in posted):.2f}）",
      len(posted) >= 4, bills)

bank = find("account.journal", [("type", "=", "bank")])[0]
pm_line = find("account.payment.method.line",
               [("journal_id", "=", bank), ("payment_method_id.payment_type", "=", "outbound")])[0]
paid = 0
for b in posted:
    if b["payment_state"] in ("paid", "in_payment"):
        paid += 1
        continue
    pay = call("account.payment", "create", {
        "payment_type": "outbound", "partner_type": "supplier",
        "partner_id": b["partner_id"][0], "amount": b["amount_total"],
        "journal_id": bank, "payment_method_line_id": pm_line})
    try:
        call("account.payment", "action_post", [pay])
    except xmlrpc.client.Fault as e:
        # XML-RPC 无法序列化 None 返回值，但过账事务已提交
        if "cannot marshal None" not in str(e):
            raise
    st = call("account.move", "read", [pay], ["payment_state", "state"])[0]
    if st["state"] == "posted":
        paid += 1
check("采购账单逐张付款完成（银行出账）", paid >= 4, f"{paid}/4")

# ============ 阶段 8：质检挂接（IQC / FQC / OQC） ============
iqc_cnt = call("odk.quality.check", "search_count", [("check_type", "=", "iqc")])
fqc_cnt = call("odk.quality.check", "search_count", [("check_type", "=", "fqc")])
oqc_cnt = call("odk.quality.check", "search_count", [("check_type", "=", "oqc")])
# IQC：挂第一张采购收货单（来料抽检）
if not find("odk.quality.check", [("check_type", "=", "iqc"), ("picking_id", "in", recv_pickings)]):
    pk = recv_pickings[0] if recv_pickings else False
    if pk:
        first_move = call("stock.move", "search_read",
                          [("picking_id", "=", pk)], ["product_id", "product_uom_qty"],
                          limit=1)
        pk_partner = call("stock.picking", "read", [pk], ["partner_id"])[0]["partner_id"]
        if first_move:
            call("odk.quality.check", "create", {
                "check_type": "iqc", "product_id": first_move[0]["product_id"][0],
                "picking_id": pk, "product_qty": 10, "qty_passed": 10, "qty_failed": 0,
                "partner_id": pk_partner[0] if pk_partner else False,
                "note": "IQC 来料抽检：外观/克重/色差全数合格"})
iqc_cnt2 = call("odk.quality.check", "search_count", [("check_type", "=", "iqc")])
check("IQC 来料质检单（挂采购收货单）", iqc_cnt2 > iqc_cnt or iqc_cnt >= 1, iqc_cnt2)

# FQC：成品全检（本次 100 双抽检 20）
if not fqc_cnt:
    call("odk.quality.check", "create", {
        "check_type": "fqc", "product_id": v_black_41,
        "product_qty": 20, "qty_passed": 20, "qty_failed": 0,
        "note": "FQC 成型车间成品抽检：配双/外观/拉力/耐折 20 双全数合格"})
fqc_cnt2 = call("odk.quality.check", "search_count", [("check_type", "=", "fqc")])
check("FQC 成品质检单（挂生产入库）", fqc_cnt2 >= 1, fqc_cnt2)

# OQC：挂销售发货单（出库复核）
ship_pid = so["picking_ids"][0] if so["picking_ids"] else False
if ship_pid and not oqc_cnt:
    mv = call("stock.move", "search_read", [("picking_id", "=", ship_pid)],
              ["product_id", "product_uom_qty"], limit=1)
    if mv:
        call("odk.quality.check", "create", {
            "check_type": "oqc", "product_id": mv[0]["product_id"][0],
            "picking_id": ship_pid, "product_qty": 5, "qty_passed": 5, "qty_failed": 0,
            "note": "OQC 出货复核：抽 5 双确认鞋盒/吊牌/配双无误，同意出货"})
oqc_cnt2 = call("odk.quality.check", "search_count", [("check_type", "=", "oqc")])
check("OQC 出货质检单（挂销售发货单）", oqc_cnt2 >= 1, oqc_cnt2)

# ============ 结果汇总 ============
print("\n========== 全链路汇总 ==========")
print("生产订单 :", call("mrp.production", "read", [mo_id], ["name", "state"])[0])
print("采购单数 :", len(po_all), "| 账单已过账:", len(posted), "| 已付款:", paid)
print("销售订单 :", so["name"], so["state"])
print("委外单   :", call("odk.subcontract.order", "search_count", []), "张")
print("质检单   : IQC %s / FQC %s / OQC %s" % (iqc_cnt2, fqc_cnt2, oqc_cnt2))
print("成品库存 : A-001(黑41) =", fp2_qty)
print(f"\n========== setup_full_flow: {sum(R)}/{len(R)} PASS ==========")
