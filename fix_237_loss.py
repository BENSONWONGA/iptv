# -*- coding: utf-8 -*-
"""修正 237单：把原表的 3% 面料损耗做进 BOM（单耗×损耗系数），作废重建 BOM 与采购申请，逐行对齐原表"""
import json

import requests
import xlrd

B = "http://220.162.99.166:88"
T = "77455c7d4b3a8fe:432939a748243fd"
s = requests.Session()
s.headers.update({"Authorization": f"token {T}", "Content-Type": "application/json"})


def lst(dt, fields, filters=None, limit=300):
    p = {"limit_page_length": limit, "fields": json.dumps(fields)}
    if filters:
        p["filters"] = json.dumps(filters)
    return s.get(f"{B}/api/resource/{dt}", params=p, timeout=30).json().get("data", [])


def save_and_submit(dt, data):
    name = s.post(f"{B}/api/resource/{dt}", json=data, timeout=60).json()["data"]["name"]
    doc = s.get(f"{B}/api/resource/{dt}/{name}", timeout=30).json()["data"]
    r2 = s.post(f"{B}/api/method/frappe.client.submit", json={"doc": doc}, timeout=60)
    assert r2.status_code == 200, r2.text[:300]
    return name


def cancel(dt, name):
    r = s.post(f"{B}/api/method/frappe.client.cancel", json={"doctype": dt, "name": name}, timeout=60)
    assert r.status_code == 200, r.text[:300]


# ---- 解析原表，计算每行损耗系数 ----
sh = xlrd.open_workbook("/workspace/.uploads/b83169b9-bd4d-4d83-9dc8-a12dfefd1e8f_237单.xls").sheet_by_index(0)
CELL = lambda r, c: sh.cell_value(r, c)
QTY = float(CELL(4, 2))
rows = []
for r in range(15, 60):
    part = str(CELL(r, 1)).strip()
    per = CELL(r, 15)
    if not part or per == "":
        continue
    sheet_total = float(CELL(r, 17) or 0)
    theo = per * QTY
    factor = round(sheet_total / theo, 4) if theo else 1.0
    rows.append({"seq": int(CELL(r, 0) or 0), "part": part, "per": float(per), "factor": factor,
                 "uom_raw": str(CELL(r, 18)).strip(), "sheet_total": sheet_total,
                 "item": f"M-25383-{int(CELL(r, 0) or 0):02d}"})
loss_rows = [r for r in rows if abs(r["factor"] - 1.03) < 0.002]
print(f"共 {len(rows)} 行，其中含 3% 损耗 {len(loss_rows)} 行：", [r["part"] for r in loss_rows][:8], "...")

UOM_MAP = {"Y": "Yard", "米": "Meter", "㎡": "Square Meter", "张": "张", "粒": "Nos", "双": "Nos"}

# ---- 作废旧的 指令单 / BOM / 采购申请（BOM 被指令单关联，须先作废指令单） ----
cancel("Sales Order", "SAL-ORD-2026-00004")
cancel("BOM", "BOM-25383-001")
cancel("Material Request", "MAT-MR-2026-00002")
print("已作废: SAL-ORD-2026-00004 / BOM-25383-001 / MAT-MR-2026-00002")

# ---- 重建指令单（同内容，不勾旧 BOM） ----
sizes = {int(CELL(5, c)): int(CELL(12, c)) for c in range(3, 9)}
size_note = " ".join(f"{k}:{v}" for k, v in sorted(sizes.items()))
so_name = save_and_submit("Sales Order", {
    "doctype": "Sales Order", "company": "奥登科鞋业有限公司", "customer": "阿瓦诺",
    "transaction_date": "2026-10-06", "delivery_date": "2026-10-30", "custom_factory_order_no": "237单",
    "items": [{"doctype": "Sales Order Item", "item_code": "25383", "qty": 3178, "delivery_date": "2026-10-30",
               "description": f"配码 {size_note}（中码38）| 深灰色 | 楦 OD-U023-B | 客户货号 149474"}]})
print("新指令单:", so_name)

# ---- 重建 BOM：单耗 × 损耗系数 ----
bom_items = [{"doctype": "BOM Item", "item_code": r["item"],
              "qty": round(r["per"] * r["factor"], 6),
              "uom": UOM_MAP[r["uom_raw"]], "stock_uom": UOM_MAP[r["uom_raw"]], "conversion_factor": 1}
             for r in rows]
bom_name = save_and_submit("BOM", {"doctype": "BOM", "item": "25383", "quantity": 1, "uom": "Nos",
                                   "is_active": 1, "is_default": 1, "items": bom_items,
                                   "company": "奥登科鞋业有限公司"})
print("新 BOM:", bom_name)

# ---- 重建采购申请（外协除外） ----
bins = {b["item_code"]: b["actual_qty"] for b in lst("Bin", ["item_code", "actual_qty"], [["actual_qty", ">", 0]], 500)}
mr_items, verify = [], []
for r in rows:
    if r["part"] == "外协":
        continue
    gross = round(r["per"] * r["factor"] * QTY, 2)
    net = round(max(0, gross - bins.get(r["item"], 0)), 2)
    verify.append((r, net))
    if net > 0:
        mr_items.append({"doctype": "Material Request Item", "item_code": r["item"], "qty": net,
                         "uom": UOM_MAP[r["uom_raw"]], "stock_uom": UOM_MAP[r["uom_raw"]], "conversion_factor": 1,
                         "warehouse": "材料仓 - 奥登科", "schedule_date": "2026-10-12"})
mr_name = save_and_submit("Material Request", {
    "doctype": "Material Request", "company": "奥登科鞋业有限公司", "material_request_type": "Purchase",
    "transaction_date": "2026-10-06", "custom_factory_order_no": "237单", "items": mr_items})
print("新采购申请:", mr_name, f"共 {len(mr_items)} 项")

# ---- 与原表逐行对账 ----
bad = 0
for r, net in verify:
    diff = abs(net - round(r["sheet_total"], 2))
    if diff > 0.05:
        bad += 1
        print(f"ERR | {r['part']} | 系统净需求 {net} | 原表 {round(r['sheet_total'],2)}")
print(f"对账: {len(verify) - bad}/{len(verify)} 一致，差异 {bad}")
json.dump({"bom": bom_name, "mr": mr_name, "ok": f"{len(verify)-bad}/{len(verify)}"},
          open("/workspace/237_fix.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
