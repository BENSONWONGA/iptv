# -*- coding: utf-8 -*-
"""流程1：销售订单(指令单号) → 生产计划MRP → 工单 + 物料申请 → 采购订单 → 采购入库"""
import json
import os
from api import (get_doc, new_doc, set_doc, submit_doc, get_list,
                 run_doc_method, whitelisted)

COMPANY = "奥登科鞋业有限公司"
STATE_FILE = "/workspace/shoe_erp/state.json"
STATE = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}


def save_state():
    json.dump(STATE, open(STATE_FILE, "w"), ensure_ascii=False, indent=1)


def log(msg, ok=True):
    print(("OK " if ok else "ERR") + " | " + msg)


def ensure_submitted(doctype, name, extra_set=None):
    d = get_doc(doctype, name)
    if d["docstatus"] == 0:
        if extra_set:
            set_doc(doctype, name, extra_set)
        submit_doc(doctype, name)
        d = get_doc(doctype, name)
        log(f"   已提交 {doctype} {name} -> docstatus={d['docstatus']} status={d.get('status')}")
    else:
        log(f"   {doctype} {name} 已提交 (status={d.get('status')})")
    return d


# ============ 1. 销售订单 ============
if "so" not in STATE:
    so = new_doc("Sales Order", {
        "customer": "美星国际贸易有限公司",
        "custom_factory_order_no": "FO-2026-001",
        "custom_style_no": "A001",
        "delivery_date": "2026-11-05",
        "items": [{
            "item_code": "FG-A001-41-BK",
            "qty": 2000,
            "rate": 120,
            "warehouse": "成品仓 - 奥登科",
            "delivery_date": "2026-11-05",
        }],
    })
    STATE["so"] = so["name"]
    save_state()
    log(f"创建销售订单: {so['name']} (工厂指令单号 FO-2026-001, 款号 A001, 2000双)")
so_name = STATE["so"]
so = ensure_submitted("Sales Order", so_name)
log(f"销售订单 {so_name}: 金额 {so.get('total')} 状态 {so.get('status')}")

# ============ 2. 生产计划（MRP） ============
if "pp" not in STATE:
    # 2.1 先在内存中拉取销售订单物料（PP 必须带 po_items 才能保存）
    local_pp = {
        "doctype": "Production Plan",
        "__islocal": 1,
        "company": COMPANY,
        "get_items_from": "Sales Order",
        "sales_orders": [{"sales_order": so_name}],
        "for_warehouse": "材料仓 - 奥登科",
        "sub_assembly_warehouse": "半成品仓 - 奥登科",
        "skip_available_sub_assembly_item": 0,
        "include_subcontracted_items": 1,
        "include_non_stock_items": 1,
        "combine_items": 1,
        "combine_sub_items": 1,
        "ignore_existing_ordered_qty": 0,
    }
    r = run_doc_method("get_items", local_pp)
    po_items = r["docs"][0].get("po_items", [])
    for row in po_items:
        log(f"   生产物料: {row.get('item_code')} x{row.get('planned_qty')} BOM={row.get('bom_no')}")
    if not po_items:
        log("get_items 未返回物料!", False)
        raise SystemExit(1)
    # 2.2 带物料创建生产计划
    pp = new_doc("Production Plan", {
        "company": COMPANY,
        "get_items_from": "Sales Order",
        "sales_orders": [{"sales_order": so_name}],
        "for_warehouse": "材料仓 - 奥登科",
        "sub_assembly_warehouse": "半成品仓 - 奥登科",
        "skip_available_sub_assembly_item": 0,
        "include_subcontracted_items": 1,
        "include_non_stock_items": 1,
        "combine_items": 1,
        "combine_sub_items": 1,
        "ignore_existing_ordered_qty": 0,
        "po_items": po_items,
    })
    STATE["pp"] = pp["name"]
    save_state()
    log(f"创建生产计划(含 {len(po_items)} 行装配物料): {pp['name']}")
pp_name = STATE["pp"]

# 2.2 分解子装配件（帮面=委外）
pp = get_doc("Production Plan", pp_name)
if not pp.get("sub_assembly_items"):
    r = run_doc_method("get_sub_assembly_items", pp)
    new_pp = r["docs"][0]
    sa = new_pp.get("sub_assembly_items", [])
    for row in sa:
        log(f"   子装配: {row.get('production_item')} x{row.get('qty')} [{row.get('type_of_manufacturing')}] 供应商={row.get('supplier')}")
    set_doc("Production Plan", pp_name, {"sub_assembly_items": sa})
else:
    log("   sub_assembly_items 已有数据")

# 2.3 提交生产计划
ensure_submitted("Production Plan", pp_name)

# ============ 3. 生成工单 + 委外采购订单 ============
pp = get_doc("Production Plan", pp_name)
wo_rows = get_list("Work Order", fields=["name", "docstatus", "production_item", "qty", "status"],
                   filters=[["production_plan", "=", pp_name]])
if not wo_rows:
    r = run_doc_method("make_work_order", pp)
    log(f"   make_work_order 返回: {str(r.get('message'))[:200]}")
    wo_rows = get_list("Work Order", fields=["name", "docstatus", "production_item", "qty", "status"],
                       filters=[["production_plan", "=", pp_name]])
log(f"工单: {[(w['name'], w['production_item'], w['qty'], w['docstatus'], w['status']) for w in wo_rows]}")
if wo_rows:
    STATE["wo"] = wo_rows[0]["name"]
    save_state()
    ensure_submitted("Work Order", wo_rows[0]["name"],
                     {"custom_factory_order_no": "FO-2026-001", "custom_style_no": "A001"})
else:
    log("未生成工单!", False)

po_sub_rows = []
for p in get_list("Purchase Order", fields=["name", "supplier", "docstatus", "status"], limit=0):
    d = get_doc("Purchase Order", p["name"])
    if d.get("production_plan") == pp_name:
        po_sub_rows.append(p)
log(f"委外PO: {[(p['name'], p['supplier'], p['docstatus'], p['status']) for p in po_sub_rows]}")
if po_sub_rows:
    STATE["po_sub"] = po_sub_rows[0]["name"]
    save_state()
    ensure_submitted("Purchase Order", po_sub_rows[0]["name"], {"custom_factory_order_no": "FO-2026-001"})
else:
    log("未生成委外PO!", False)

# ============ 3.5 手动创建委外采购订单（服务器版 PP 不自动生成） ============
pp = get_doc("Production Plan", pp_name)
if "po_sub" not in STATE or not STATE.get("po_sub"):
    sa_row = next((r for r in pp.get("sub_assembly_items", [])
                   if r.get("type_of_manufacturing") == "Subcontract"), None)
    if sa_row:
        try:
            po = new_doc("Purchase Order", {
                "supplier": sa_row.get("supplier") or "莆田华盛针车厂",
                "company": COMPANY,
                "is_subcontracted": 1,
                "custom_factory_order_no": "FO-2026-001",
                "schedule_date": "2026-10-15",
                "set_warehouse": "半成品仓 - 奥登科",
                "production_plan": pp_name,
                "items": [{
                    "item_code": "SVC-STI",
                    "fg_item": "SF-A001",
                    "fg_item_qty": 2000,
                    "qty": 2000,
                    "uom": "双",
                    "rate": 12,
                    "warehouse": "半成品仓 - 奥登科",
                    "bom": "BOM-SF-A001-001",
                    "schedule_date": "2026-10-15",
                    "production_plan": pp_name,
                    "production_plan_sub_assembly_item": sa_row.get("name"),
                }],
            })
            STATE["po_sub"] = po["name"]
            save_state()
            log(f"创建委外采购订单 {po['name']}: 帮面针车 2000双 @12元/双")
        except Exception as e:
            log(f"委外PO创建失败: {str(e)[:300]}", False)
    else:
        log("未找到 Subcontract 类型的子装配行", False)
if STATE.get("po_sub"):
    ensure_submitted("Purchase Order", STATE["po_sub"], {"custom_factory_order_no": "FO-2026-001"})

# ============ 4. MRP 物料需求 → 物料申请（直接创建 MR） ============
pp = get_doc("Production Plan", pp_name)
if "mr" not in STATE or not STATE.get("mr"):
    import json as _json
    r = whitelisted("erpnext.manufacturing.doctype.production_plan.production_plan.get_items_for_material_requests",
                    doc=_json.dumps(pp), warehouses=[])
    mr_rows = r.get("message", [])
    sa_items = {row.get("production_item") for row in (pp.get("sub_assembly_items") or [])}
    filtered = []
    for row in mr_rows:
        if row.get("item_code") in sa_items:
            log(f"   过滤委外半成品(不走MR): {row.get('item_code')} x{row.get('quantity')}")
            continue
        filtered.append(row)
        log(f"   物料需求: {row.get('item_code')} x {row.get('quantity')} -> {row.get('warehouse')}")
    if filtered:
        mr_items = []
        for row in filtered:
            mr_items.append({
                "item_code": row.get("item_code"),
                "qty": row.get("quantity"),
                "uom": row.get("stock_uom"),
                "conversion_factor": 1,
                "warehouse": row.get("warehouse") or "材料仓 - 奥登科",
                "schedule_date": "2026-10-12",
                "sales_order": so_name,
                "production_plan": pp_name,
            })
        mr = new_doc("Material Request", {
            "material_request_type": "Purchase",
            "transaction_date": "2026-10-05",
            "company": COMPANY,
            "custom_factory_order_no": "FO-2026-001",
            "items": mr_items,
        })
        STATE["mr"] = mr["name"]
        save_state()
        log(f"创建物料申请 {mr['name']}: {len(mr_items)} 种材料")

pp = get_doc("Production Plan", pp_name)
mr_rows_db = get_list("Material Request", fields=["name", "docstatus", "status", "material_request_type"], limit=0)
mr_rows_db = [m for m in mr_rows_db if get_doc("Material Request", m["name"]).get("production_plan") == pp_name or m["name"] == STATE.get("mr")]
log(f"物料申请: {[(m['name'], m['status'], m['docstatus']) for m in mr_rows_db]}")
if STATE.get("mr"):
    ensure_submitted("Material Request", STATE["mr"])
    mr_rows_db = [STATE["mr"]]

# ============ 5. 采购订单（两家材料供应商） ============
if "po1" not in STATE or "po2" not in STATE:
    mr_name = STATE.get("mr")
    mr_items = get_doc("Material Request", mr_name).get("items") if mr_name else []
    sup_map = {
        "M-FAB-001": ("泉州兴发纺织有限公司", 25),
        "M-LIN-001": ("泉州兴发纺织有限公司", 8),
        "M-ACC-001": ("东莞宏力鞋材有限公司", 0.3),
        "M-ACC-002": ("东莞宏力鞋材有限公司", 2),
        "M-BOT-001": ("东莞宏力鞋材有限公司", 18),
        "M-BOT-002": ("东莞宏力鞋材有限公司", 6),
        "M-CHE-001": ("东莞宏力鞋材有限公司", 15),
    }
    pos = {
        "泉州兴发纺织有限公司": [],
        "东莞宏力鞋材有限公司": [],
    }
    for it in mr_items:
        code = it.get("item_code")
        if code in sup_map:
            sup, rate = sup_map[code]
            pos[sup].append({
                "item_code": code,
                "qty": it.get("qty"),
                "rate": rate,
                "warehouse": "材料仓 - 奥登科",
                "schedule_date": "2026-10-12",
                "material_request": mr_name,
                "material_request_item": it.get("name"),
            })
    for sup, items in pos.items():
        if not items:
            continue
        if (sup.startswith("泉州") and "po1" in STATE) or (sup.startswith("东莞") and "po2" in STATE):
            continue
        po = new_doc("Purchase Order", {
            "supplier": sup,
            "custom_factory_order_no": "FO-2026-001",
            "set_warehouse": "材料仓 - 奥登科",
            "schedule_date": "2026-10-12",
            "items": items,
        })
        key = "po1" if sup.startswith("泉州") else "po2"
        STATE[key] = po["name"]
        save_state()
        log(f"创建采购订单 {po['name']}: {sup} {len(items)} 种材料")
    for key in ["po1", "po2"]:
        if key in STATE:
            ensure_submitted("Purchase Order", STATE[key], {"custom_factory_order_no": "FO-2026-001"})

# ============ 6. 采购入库（材料入材料仓） ============
for key in ["po1", "po2"]:
    if key not in STATE:
        continue
    pr_key = "pr_" + key
    if pr_key in STATE:
        d = get_doc("Purchase Receipt", STATE[pr_key])
        log(f"采购入库 {STATE[pr_key]} docstatus={d['docstatus']}")
        if d["docstatus"] == 0:
            submit_doc("Purchase Receipt", STATE[pr_key])
        continue
    po_name = STATE[key]
    r = whitelisted("erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
                    source_name=po_name)
    mapped = r.get("message")
    if isinstance(mapped, dict) and mapped.get("items"):
        mapped["custom_factory_order_no"] = "FO-2026-001"
        mapped.pop("name", None)
        # 清理映射行的 name，避免重复
        for it in mapped.get("items", []):
            it.pop("name", None)
        pr_doc = new_doc("Purchase Receipt", mapped)
        pr_name = pr_doc["name"]
        STATE[pr_key] = pr_name
        save_state()
        log(f"创建采购入库 {pr_name} <- {po_name}（{len(mapped['items'])} 项）")
        ensure_submitted("Purchase Receipt", pr_name, {"custom_factory_order_no": "FO-2026-001"})
    else:
        log(f"make_purchase_receipt 异常: {str(r)[:300]}", False)

print("\n===== 流程1完成 =====")
print(json.dumps(STATE, ensure_ascii=False, indent=1))
