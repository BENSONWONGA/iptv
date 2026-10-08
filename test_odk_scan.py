# -*- coding: utf-8 -*-
"""odk_scan 端到端测试：登录 → 建仓库/物料 → act_lookup → act_transfer → 验证调拨已过账"""
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
    print(("[PASS] " if ok else "[FAIL] ") + name + ("" if ok else "  --> " + str(detail)[:150]))


# 1) 建两个仓库（奥登科 材料仓 / 成品仓）
wh_ids = call("stock.warehouse", "search", [])
whs = call("stock.warehouse", "read", wh_ids, ["name", "code"])
check("默认仓库存在（stock 已初始化）", len(whs) >= 1, whs)
if len(whs) < 2:
    call("stock.warehouse", "create", {"name": "成品仓", "code": "WH2"})
    whs = call("stock.warehouse", "read", call("stock.warehouse", "search", []), ["name", "code"])
# 重命名为中文便于演示
call("stock.warehouse", "write", [whs[0]["id"]], {"name": "材料仓"})
if len(whs) > 1:
    call("stock.warehouse", "write", [whs[1]["id"]], {"name": "成品仓"})
whs = call("stock.warehouse", "read", call("stock.warehouse", "search", []), ["name", "code"])
print("仓库:", [(w["name"], w["code"]) for w in whs])
wh_from, wh_to = whs[0]["id"], whs[1]["id"]

# 2) 建带条码的物料 + 先放 100 件到材料仓（用 inventory adjustment 做期初）
cat_id = call("product.category", "search", [], limit=1)[0]
exist = call("product.product", "search", [("default_code", "=", "M-FAB-001")], limit=1)
if exist:
    prod_id = exist[0]
    check("物料已存在，复用", True)
else:
    prod_id = call("product.product", "create", {
        "name": "牛巴戈面料(黑色)", "default_code": "M-FAB-001", "barcode": "6901234500011",
        "type": "consu", "is_storable": True, "categ_id": cat_id,
        "uom_id": call("uom.uom", "search", [("name", "=", "Units")], limit=1)[0],
    })
    check("创建带条码物料", bool(prod_id))
# v20 期初库存：直接建 quant（幂等：已有则补足到 100）
def qty_at(wh_id):
    loc = call("stock.warehouse", "read", [wh_id], ["lot_stock_id"])[0]["lot_stock_id"][0]
    q = call("stock.quant", "search_read", [("product_id", "=", prod_id), ("location_id", "=", loc)], ["quantity"])
    return sum(x["quantity"] for x in q)


loc_from = call("stock.warehouse", "read", [wh_from], ["lot_stock_id"])[0]["lot_stock_id"][0]
if qty_at(wh_from) < 100:
    call("stock.quant", "create", {"product_id": prod_id, "location_id": loc_from, "quantity": 100 - qty_at(wh_from)})
check("期初库存入材料仓（≥100）", qty_at(wh_from) >= 100)

# 3) act_lookup 条码识别
item = call("odk.scan", "act_lookup", barcode="6901234500011")
check("act_lookup 条码识别", item.get("code") == "M-FAB-001", item)

# 4) act_transfer 调拨 5 件 材料仓→成品仓（增量断言，重复运行稳定）
q_from_b, q_to_b = qty_at(wh_from), qty_at(wh_to)
res = call("odk.scan", "act_transfer", barcode="6901234500011", qty=5, from_id=wh_from, to_id=wh_to, fo_ref="237单")
check("act_transfer 生成并过账调拨", res.get("state") == "done", res)
print("调拨单:", res)

q_from_a, q_to_a = qty_at(wh_from), qty_at(wh_to)
check(f"库存账变动：材料仓 {q_from_b}→{q_from_a} / 成品仓 {q_to_b}→{q_to_a}",
      abs(q_from_a - (q_from_b - 5)) < 0.01 and abs(q_to_a - (q_to_b + 5)) < 0.01)

# 6) 异常分支：条码不存在
try:
    call("odk.scan", "act_transfer", barcode="NOT-EXIST", qty=1, from_id=wh_from, to_id=wh_to)
    check("未知条码被拒绝", False, "未抛错")
except Exception as e:
    check("未知条码被拒绝", "未找到对应物料" in str(e), str(e)[:80])

print(f"\n========== odk_scan 测试: {sum(R)}/{len(R)} PASS ==========")
