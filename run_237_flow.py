# -*- coding: utf-8 -*-
"""237单 走流程：客户 → 成品/物料档案 → 指令单(提交) → BOM(提交) → MRP净需求 → 采购申请(提交)"""
import json
import time

import requests
import xlrd

B = "http://220.162.99.166:88"
T = "77455c7d4b3a8fe:432939a748243fd"
s = requests.Session()
s.headers.update({"Authorization": f"token {T}", "Content-Type": "application/json"})
CREATED = []


def lst(dt, fields, filters=None, limit=200):
    p = {"limit_page_length": limit, "fields": json.dumps(fields)}
    if filters:
        p["filters"] = json.dumps(filters)
    return s.get(f"{B}/api/resource/{dt}", params=p, timeout=30).json().get("data", [])


def save_and_submit(dt, data):
    r = s.post(f"{B}/api/resource/{dt}", json=data, timeout=60)
    if r.status_code not in (200, 200):
        print("创建失败", dt, r.text[:300]); raise SystemExit(1)
    name = r.json()["data"]["name"]
    doc = s.get(f"{B}/api/resource/{dt}/{name}", timeout=30).json()["data"]
    r2 = s.post(f"{B}/api/method/frappe.client.submit", json={"doc": doc}, timeout=60)
    if r2.status_code != 200:
        print("提交失败", dt, name, r2.text[:300]); raise SystemExit(1)
    CREATED.append((dt, name))
    return name


def ensure(dt, filters, data):
    hit = lst(dt, ["name"], filters, 5)
    if hit:
        return hit[0]["name"], False
    name = s.post(f"{B}/api/resource/{dt}", json=data, timeout=60).json()["data"]["name"]
    CREATED.append((dt, name))
    return name, True


# ---------- 0. 解析指令单 ----------
f = "/workspace/.uploads/b83169b9-bd4d-4d83-9dc8-a12dfefd1e8f_237单.xls"
sh = xlrd.open_workbook(f).sheet_by_index(0)
CELL = lambda r, c: sh.cell_value(r, c)
ORDER = {
    "no": str(CELL(1, 0)).split("：")[1],          # 237单
    "customer": str(CELL(1, 5)).split("：")[1],     # 阿瓦诺
    "our_ref": str(CELL(2, 0)).split("：")[1],     # 25383
    "cust_ref": str(CELL(2, 5)).split("：")[1],    # 149474
    "color": str(CELL(3, 0)).split("：")[1],       # 深灰色
    "last": str(CELL(3, 5)).split("：")[1],        # OD-U023-B
    "qty": float(CELL(4, 2)),                       # 3178
    "due": "2026-10-30",
    "sizes": {int(CELL(5, c)): int(CELL(12, c)) for c in range(3, 9)},
}
print("订单解析:", json.dumps(ORDER, ensure_ascii=False))

# 用料明细：行 15-59
bom_rows = []
for r in range(15, 60):
    part = str(CELL(r, 1)).strip()
    per = CELL(r, 15)
    if not part or per == "":
        continue
    uom_raw = str(CELL(r, 18)).strip()
    bom_rows.append({
        "seq": int(CELL(r, 0) or 0),
        "part": part,
        "desc": str(CELL(r, 4) or "").strip(),
        "spec": str(CELL(r, 3) or "").strip(),
        "per": float(per),
        "uom_raw": uom_raw,
        "sheet_total": float(CELL(r, 17) or 0),
    })
print(f"用料明细 {len(bom_rows)} 行")
assert abs(sum(ORDER["sizes"].values()) - ORDER["qty"]) < 0.01, "配码合计 != 订单数量"

# ---------- 1. 计量单位映射 ----------
UOM_MAP = {"Y": "Yard", "米": "Meter", "㎡": "Square Meter", "张": "张", "粒": "Nos", "双": "Nos"}
have_uoms = {u["name"] for u in lst("UOM", ["name"], None, 300)}
for u, whole in [("Meter", 0), ("张", 0)]:
    if u not in have_uoms:
        s.post(f"{B}/api/resource/UOM", json={"doctype": "UOM", "uom_name": u, "must_be_whole_number": whole}, timeout=30)
        have_uoms.add(u)

# ---------- 2. 客户 ----------
groups = [g["name"] for g in lst("Customer Group", ["name"], None, 50)]
group = "外贸客户" if "外贸客户" in groups else groups[0]
cust, _ = ensure("Customer", [["name", "like", "%阿瓦诺%"]],
                 {"doctype": "Customer", "customer_name": ORDER["customer"], "customer_type": "Company", "customer_group": group})
print("客户:", cust)

# ---------- 3. 物料档案（45 项）+ 成品 ----------
def pick_group(part, desc):
    if part == "外协":
        return "委外加工服务"
    if "底" in part or "大底" in desc:
        return "底材"
    if any(k in desc for k in ["网布", "太空", "革", "布", "海绵", "EVA", "切片", "热熔"]):
        return "面料"
    if any(k in desc for k in ["织带", "车线", "扣", "防水条", "鞋带", "港宝", "衬"]):
        return "辅料"
    return "辅料"

material_items = []
for row in bom_rows:
    code = f"M-{ORDER['our_ref']}-{row['seq']:02d}"
    name = (row["part"] + " " + row["desc"]).strip()[:140]
    is_service = row["part"] == "外协"
    data = {"doctype": "Item", "item_code": code, "item_name": name,
            "item_group": pick_group(row["part"], row["desc"]),
            "stock_uom": "Nos" if is_service else UOM_MAP[row["uom_raw"]],
            "is_stock_item": 0 if is_service else 1}
    code_name, _ = ensure("Item", [["name", "=", code]], data)
    # 修正旧档案里不一致的计量单位（如上次以 Nos 建的「张」类物料）
    want_uom = data["stock_uom"]
    cur = s.get(f"{B}/api/resource/Item/{code_name}", timeout=30).json()["data"]
    if cur.get("stock_uom") != want_uom:
        s.put(f"{B}/api/resource/Item/{code_name}", json={"stock_uom": want_uom}, timeout=30)
    row["item"] = code_name
    material_items.append(code_name)
print(f"物料档案 {len(material_items)} 项（含 1 项外协服务）")

fg_code = ORDER["our_ref"]
fg, _ = ensure("Item", [["name", "=", fg_code]],
               {"doctype": "Item", "item_code": fg_code,
                "item_name": f"{fg_code} {ORDER['color']}（楦 {ORDER['last']} / 客户货号 {ORDER['cust_ref']}）",
                "item_group": "成品鞋", "stock_uom": "Nos", "is_stock_item": 1})
print("成品:", fg)

# ---------- 4. BOM（每双用量，基数 1） ----------
bom_items = [{"doctype": "BOM Item", "item_code": r["item"], "qty": r["per"],
              "uom": UOM_MAP[r["uom_raw"]], "stock_uom": UOM_MAP[r["uom_raw"]], "conversion_factor": 1}
             for r in bom_rows]
bom_name = save_and_submit("BOM", {
    "doctype": "BOM", "item": fg, "quantity": 1, "uom": "Nos",
    "is_active": 1, "is_default": 1, "items": bom_items, "company": "奥登科鞋业有限公司"})
print("BOM:", bom_name)

# ---------- 5. 指令单（销售订单）并提交 ----------
size_note = " ".join(f"{k}:{v}" for k, v in sorted(ORDER["sizes"].items()))
so_name = save_and_submit("Sales Order", {
    "doctype": "Sales Order", "company": "奥登科鞋业有限公司",
    "customer": cust, "transaction_date": "2026-10-06", "delivery_date": ORDER["due"],
    "custom_factory_order_no": ORDER["no"],
    "items": [{"doctype": "Sales Order Item", "item_code": fg, "qty": ORDER["qty"],
               "delivery_date": ORDER["due"],
               "description": f"配码 {size_note}（中码38）| {ORDER['color']} | 楦 {ORDER['last']} | 客户货号 {ORDER['cust_ref']}"}]})
print("指令单:", so_name)

# ---------- 6. MRP：毛需求 - 现有库存 = 净需求 ----------
bins = {b["item_code"]: b["actual_qty"] for b in lst("Bin", ["item_code", "actual_qty"], [["actual_qty", ">", 0]], 500)}
mr_items, verify = [], []
for r in bom_rows:
    if r["part"] == "外协":
        verify.append((r, None, "外协走委外流程，不入采购申请"))
        continue
    gross = round(r["per"] * ORDER["qty"], 3)
    stock = bins.get(r["item"], 0)
    net = round(max(0, gross - stock), 2)
    verify.append((r, net, ""))
    if net > 0:
        mr_items.append({"doctype": "Material Request Item", "item_code": r["item"], "qty": net,
                         "uom": UOM_MAP[r["uom_raw"]], "stock_uom": UOM_MAP[r["uom_raw"]],
                         "conversion_factor": 1, "warehouse": "材料仓 - 奥登科",
                         "schedule_date": "2026-10-12"})
mr_name = save_and_submit("Material Request", {
    "doctype": "Material Request", "company": "奥登科鞋业有限公司",
    "material_request_type": "Purchase", "transaction_date": "2026-10-06",
    "custom_factory_order_no": ORDER["no"], "items": mr_items})
print("采购申请(MRP):", mr_name, f"共 {len(mr_items)} 项")

# ---------- 7. 与原表逐行对账 ----------
print("\n===== 与 Excel 原表耗量对账 =====")
bad = 0
for r, net, note in verify:
    sheet = round(r["per"] * ORDER["qty"], 2)
    diff = abs(sheet - round(r["sheet_total"], 2))
    ok = diff < 0.05
    if not ok:
        bad += 1
    print(("OK " if ok else "ERR") + f" | {r['part']:<6} | 每双{r['per']} {r['uom_raw']} | 系统算 {sheet} | 原表 {round(r['sheet_total'],2)}"
          + (" | 净需求 " + str(net) if net is not None else " | " + note))
print(f"\n对账: {len(verify) - bad}/{len(verify)} 一致，差异 {bad}")
print("创建清单:", json.dumps(CREATED, ensure_ascii=False))
json.dump({"order": ORDER, "created": CREATED, "mr": mr_name, "so": so_name, "bom": bom_name},
          open("/workspace/237_result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
