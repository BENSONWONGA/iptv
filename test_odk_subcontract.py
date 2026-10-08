# -*- coding: utf-8 -*-
"""odk_subcontract 端到端测试：建委外供应商/成品/BOM → 建委外加工单 → BOM 带料
→ 确认发料（组件出库）→ 成品收货（成品入库）→ 异常分支"""
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


def ensure_product(code, name, **kw):
    ids = call("product.product", "search", [("default_code", "=", code)], limit=1)
    if ids:
        return ids[0]
    vals = {"name": name, "default_code": code, "type": "consu", "is_storable": True,
            "categ_id": call("product.category", "search", [], limit=1)[0],
            "uom_id": call("uom.uom", "search", [("name", "=", "Units")], limit=1)[0]}
    vals.update(kw)
    return call("product.product", "create", vals)


def qty_at(loc_id, prod_id):
    q = call("stock.quant", "search_read",
             [("product_id", "=", prod_id), ("location_id", "=", loc_id)], ["quantity"])
    return sum(x["quantity"] for x in q)


def stock_loc_of(wh_id):
    return call("stock.warehouse", "read", [wh_id], ["lot_stock_id"])[0]["lot_stock_id"][0]


def top_up(loc_id, prod_id, target):
    """把 loc_id 处 prod_id 库存补足到 target（幂等）"""
    if qty_at(loc_id, prod_id) < target:
        call("stock.quant", "create", {
            "product_id": prod_id, "location_id": loc_id,
            "quantity": target - qty_at(loc_id, prod_id)})


# ── 1) 基础数据 ────────────────────────────────────────────────
whs = call("stock.warehouse", "search_read", [], ["name", "code"])
wh_main = whs[0]["id"]
loc_main = stock_loc_of(wh_main)
print("仓库:", [(w["name"], w["code"]) for w in whs])

p_fab = ensure_product("M-FAB-001", "牛巴戈面料(黑色)")
p_lin = ensure_product("M-LIN-001", "猪皮内里(米色)")
p_upper = ensure_product("S-UPPER-237", "237款帮面(白色)")

vender_ids = call("res.partner", "search", [("name", "=", "宏达针车厂")], limit=1)
if not vender_ids:
    vender_ids = [call("res.partner", "create", {"name": "宏达针车厂", "is_company": True})]
p_vendor = vender_ids[0]
check("委外供应商就绪", bool(p_vendor))

# BOM：1 双帮面 = 2 面料 + 1 内里（幂等：有则复用）
tmpl = call("product.product", "read", [p_upper], ["product_tmpl_id"])[0]["product_tmpl_id"][0]
bom_ids = call("mrp.bom", "search", [("product_tmpl_id", "=", tmpl)], limit=1)
if not bom_ids:
    bom_ids = [call("mrp.bom", "create", {
        "product_tmpl_id": tmpl, "product_qty": 1.0,
        "bom_line_ids": [
            (0, 0, {"product_id": p_fab, "product_qty": 2.0,
                    "uom_id": call("uom.uom", "search", [("name", "=", "Units")], limit=1)[0]}),
            (0, 0, {"product_id": p_lin, "product_qty": 1.0,
                    "uom_id": call("uom.uom", "search", [("name", "=", "Units")], limit=1)[0]}),
        ],
    })]
bom = bom_ids[0]
check("BOM 就绪（1 帮面 = 2 面料 + 1 内里）", bool(bom))

# 期初：面料 ≥ 200、内里 ≥ 100（幂等补足）
top_up(loc_main, p_fab, 200)
top_up(loc_main, p_lin, 100)
check("期初库存就绪", qty_at(loc_main, p_fab) >= 200 and qty_at(loc_main, p_lin) >= 100)

# 委外供应商虚拟库位：清掉历史运行残留（保证在制断言为绝对值）
sub_loc = call("res.partner", "read", [p_vendor], ["property_stock_supplier"])[0]["property_stock_supplier"]
sub_loc = sub_loc[0] if sub_loc else call("stock.location", "search",
                                          [("usage", "=", "supplier")], limit=1)[0]
for pid in (p_fab, p_lin, p_upper):
    q = qty_at(sub_loc, pid)
    if abs(q) > 0.001:
        call("stock.quant", "create", {"product_id": pid, "location_id": sub_loc, "quantity": -q})
check("委外库位残留已清零", all(abs(qty_at(sub_loc, pid)) < 0.001 for pid in (p_fab, p_lin)))

# ── 2) 建委外加工单：10 双帮面，BOM 自动带料 ──────────────────
order_id = call("odk.subcontract.order", "create", {
    "partner_id": p_vendor, "warehouse_id": wh_main,
    "product_id": p_upper, "product_qty": 10.0, "bom_id": bom,
    "price_unit": 15.0,
})
call("odk.subcontract.order", "action_fill_components", [order_id])
order = call("odk.subcontract.order", "read", [order_id],
             ["name", "state", "amount_total", "component_ids"])[0]
lines = call("odk.subcontract.order.line", "read", order["component_ids"],
             ["product_id", "product_qty"])
by_prod = {l["product_id"][0]: l["product_qty"] for l in lines}
check("BOM 自动带料：10 双 → 面料×20 + 内里×10",
      abs(by_prod.get(p_fab, 0) - 20) < 0.01 and abs(by_prod.get(p_lin, 0) - 10) < 0.01, by_prod)
check("加工金额 = 15 × 10 = 150", abs(order["amount_total"] - 150.0) < 0.01, order["amount_total"])
check("初始状态为草稿", order["state"] == "draft", order["state"])
print("委外单:", order["name"])

# ── 3) 确认发料：组件出库给委外供应商 ────────────────────────
q_fab_b, q_lin_b, q_up_b = (qty_at(loc_main, p_fab), qty_at(loc_main, p_lin), qty_at(loc_main, p_upper))
call("odk.subcontract.order", "action_confirm", [order_id])
order = call("odk.subcontract.order", "read", [order_id],
             ["state", "picking_out_id", "picking_in_id"])[0]
check("确认后状态 = 已发料", order["state"] == "confirmed", order["state"])
check("发料单已生成并过账", bool(order["picking_out_id"]), order["state"])
po = call("stock.picking", "read", [order["picking_out_id"][0]], ["state", "name"])[0]
check("发料单状态 = done", po["state"] == "done", po)
q_fab_a, q_lin_a = qty_at(loc_main, p_fab), qty_at(loc_main, p_lin)
check(f"发料后库存：面料 {q_fab_b}→{q_fab_a}（-20）/ 内里 {q_lin_b}→{q_lin_a}（-10）",
      abs(q_fab_a - (q_fab_b - 20)) < 0.01 and abs(q_lin_a - (q_lin_b - 10)) < 0.01)

# 中间库位应有在制组件（发给供应商的料）
check("委外供应商虚拟库位有 20 面料 + 10 内里（在制）",
      abs(qty_at(sub_loc, p_fab) - 20) < 0.01 and abs(qty_at(sub_loc, p_lin) - 10) < 0.01,
      (qty_at(sub_loc, p_fab), qty_at(sub_loc, p_lin)))

# ── 4) 成品收货：帮面 10 双入库 ──────────────────────────────
call("odk.subcontract.order", "action_receive", [order_id])
order = call("odk.subcontract.order", "read", [order_id],
             ["state", "picking_in_id"])[0]
check("收货后状态 = 已收货", order["state"] == "done", order["state"])
check("收货单已生成并过账", bool(order["picking_in_id"]))
pi = call("stock.picking", "read", [order["picking_in_id"][0]], ["state"])[0]
check("收货单状态 = done", pi["state"] == "done", pi)
q_up_a = qty_at(loc_main, p_upper)
check(f"帮面入库 {q_up_b}→{q_up_a}（+10）", abs(q_up_a - (q_up_b + 10)) < 0.01)
check("委外库位在制料已清零",
      abs(qty_at(sub_loc, p_fab)) < 0.01 and abs(qty_at(sub_loc, p_lin)) < 0.01)

# ── 5) 异常分支 ───────────────────────────────────────────────
# a) 草稿单不能收货
o2 = call("odk.subcontract.order", "create", {
    "partner_id": p_vendor, "warehouse_id": wh_main,
    "product_id": p_upper, "product_qty": 5.0, "bom_id": bom})
try:
    call("odk.subcontract.order", "action_receive", [o2])
    check("草稿单收货被拒绝", False, "未抛错")
except Exception as e:
    check("草稿单收货被拒绝", "已发料" in str(e), str(e)[:80])

# b) 草稿单可取消 → 退回草稿
call("odk.subcontract.order", "action_cancel", [o2])
check("草稿单可取消", call("odk.subcontract.order", "read", [o2], ["state"])[0]["state"] == "cancel")
call("odk.subcontract.order", "action_draft", [o2])
check("已取消单可退回草稿", call("odk.subcontract.order", "read", [o2], ["state"])[0]["state"] == "draft")

# c) 已收货单不能取消
try:
    call("odk.subcontract.order", "action_cancel", [order_id])
    check("已收货单取消被拒绝", False, "未抛错")
except Exception as e:
    check("已收货单取消被拒绝", "已收货" in str(e), str(e)[:80])

# d) 未选 BOM 的单不能自动带料
o3 = call("odk.subcontract.order", "create", {
    "partner_id": p_vendor, "warehouse_id": wh_main,
    "product_id": p_upper, "product_qty": 3.0})
try:
    call("odk.subcontract.order", "action_fill_components", [o3])
    check("无 BOM 带料被拒绝", False, "未抛错")
except Exception as e:
    check("无 BOM 带料被拒绝", "BOM" in str(e), str(e)[:80])

print(f"\n========== odk_subcontract 测试: {sum(R)}/{len(R)} PASS ==========")
