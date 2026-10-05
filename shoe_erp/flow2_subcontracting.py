# -*- coding: utf-8 -*-
"""流程2：委外加工（PO→SCO→发料给委外厂→委外收货=半成品入库）"""
import json
import os
from api import (get_doc, new_doc, set_doc, submit_doc, get_list, whitelisted)

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
        log(f"   已提交 {doctype} {name} -> {d['docstatus']} {d.get('status')}")
    else:
        log(f"   {doctype} {name} 已提交 (status={d.get('status')})")
    return d


po_sub = STATE.get("po_sub")
assert po_sub, "缺少委外PO"

# ============ 1. 生成委外订单 SCO ============
if "sco" not in STATE:
    r = whitelisted("erpnext.buying.doctype.purchase_order.purchase_order.make_subcontracting_order",
                    source_name=po_sub)
    mapped = r.get("message")
    if isinstance(mapped, dict) and mapped.get("purchase_order"):
        # 补充必填字段后入库
        mapped["supplier_warehouse"] = "委外供应商仓 - 奥登科"
        mapped["custom_factory_order_no"] = "FO-2026-001"
        mapped.pop("name", None)
        for tbl in ("items", "service_items", "supplied_items", "additional_costs"):
            for row in mapped.get(tbl) or []:
                row.pop("name", None)
                row.pop("parent", None)
                row["doctype"] = {
                    "items": "Subcontracting Order Item",
                    "service_items": "Subcontracting Order Service Item",
                    "supplied_items": "Subcontracting Order Supplied Item",
                    "additional_costs": "Landed Cost Taxes and Charges",
                }[tbl]
        sco_doc = new_doc("Subcontracting Order", mapped)
        STATE["sco"] = sco_doc["name"]
        save_state()
        log(f"创建委外订单 {sco_doc['name']} <- PO {po_sub}")
    else:
        log(f"make_subcontracting_order 返回异常: {str(r)[:300]}", False)
        raise SystemExit(1)
sco_name = STATE["sco"]
sco = get_doc("Subcontracting Order", sco_name)
log(f"SCO 详情: 供应商={sco['supplier']} 主项={[(i.get('item_code'), i.get('qty')) for i in sco.get('items', [])]} "
    f"服务项={[(i.get('item_code'), i.get('qty'), i.get('rate')) for i in sco.get('service_items', [])]}")
log(f"      供货项={[(i.get('main_item_code'), i.get('qty')) for i in sco.get('supplied_items', [])]}")

# ============ 2. 设置委外仓并提交 SCO ============
sco = get_doc("Subcontracting Order", sco_name)
if sco["docstatus"] == 0:
    set_doc("Subcontracting Order", sco_name, {
        "supplier_warehouse": "委外供应商仓 - 奥登科",
        "custom_factory_order_no": "FO-2026-001",
    })
ensure_submitted("Subcontracting Order", sco_name,
                 {"supplier_warehouse": "委外供应商仓 - 奥登科", "custom_factory_order_no": "FO-2026-001"})

# ============ 3. 发料给委外厂（Stock Entry: Send to Subcontractor） ============
if "se_transfer" not in STATE:
    r = whitelisted("erpnext.controllers.subcontracting_controller.make_rm_stock_entry",
                    subcontract_order=sco_name, order_doctype="Subcontracting Order")
    se_mapped = r.get("message")
    if not isinstance(se_mapped, dict) or se_mapped.get("doctype") != "Stock Entry":
        log(f"make_rm_stock_entry 返回异常: {str(r)[:300]}", False)
        raise SystemExit(1)
    se_mapped["custom_factory_order_no"] = "FO-2026-001"
    se_mapped.pop("name", None)
    rows = se_mapped.get("items", [])
    for it in rows:
        it.pop("name", None)
        # 材料存放在材料仓，从材料仓发料给委外厂
        it["s_warehouse"] = "材料仓 - 奥登科"
    se = new_doc("Stock Entry", se_mapped)
    STATE["se_transfer"] = se["name"]
    save_state()
    log(f"创建发料单 {se['name']} 用途={se.get('purpose')}: "
        f"{[(c.get('item_code'), c.get('qty'), c.get('s_warehouse'), '->', c.get('t_warehouse')) for c in rows]}")
ensure_submitted("Stock Entry", STATE["se_transfer"], {"custom_factory_order_no": "FO-2026-001"})

# ============ 4. 委外收货（半成品帮面入库） ============
if "scr" not in STATE:
    r = whitelisted("erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order.make_subcontracting_receipt",
                    source_name=sco_name)
    mapped = r.get("message")
    if not isinstance(mapped, dict) or not mapped.get("items"):
        log(f"make_subcontracting_receipt 异常: {str(r)[:300]}", False)
        raise SystemExit(1)
    mapped["custom_factory_order_no"] = "FO-2026-001"
    for it in mapped.get("items", []):
        it.pop("name", None)
    scr = new_doc("Subcontracting Receipt", mapped)
    STATE["scr"] = scr["name"]
    save_state()
    log(f"创建委外收货单 {scr['name']}: {[(i.get('item_code'), i.get('qty'), i.get('warehouse')) for i in mapped.get('items', [])]}")
ensure_submitted("Subcontracting Receipt", STATE["scr"], {"custom_factory_order_no": "FO-2026-001"})

# ============ 5. 验证库存 ============
log("=== 委外供应商仓库存 ===")
for b in get_list("Bin", fields=["item_code", "warehouse", "actual_qty"],
                 filters=[["warehouse", "=", "委外供应商仓 - 奥登科"]], limit=0):
    log(f"  {b['item_code']}: {b['actual_qty']}")
log("=== 半成品仓库存 ===")
for b in get_list("Bin", fields=["item_code", "warehouse", "actual_qty"],
                 filters=[["warehouse", "=", "半成品仓 - 奥登科"]], limit=0):
    log(f"  {b['item_code']}: {b['actual_qty']}")

print("\n===== 流程2完成 =====")
print(json.dumps(STATE, ensure_ascii=False, indent=1))
