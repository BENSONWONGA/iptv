# -*- coding: utf-8 -*-
"""流程3：工单领料 -> MES工序报工(Job Card) -> 成品完工入库"""
import json
import os
from api import get_doc, new_doc, set_doc, submit_doc, get_list, whitelisted

WO = "MFG-WO-2026-00001"
JC = "PO-JOB00001"
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


# ============ 1. 领料：材料仓/半成品仓 -> 在制品仓(WIP) ============
if "se_mfg_transfer" not in STATE:
    r = whitelisted("erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry",
                    work_order_id=WO, purpose="Material Transfer for Manufacture")
    mapped = r.get("message")
    if not isinstance(mapped, dict) or mapped.get("doctype") != "Stock Entry":
        log(f"make_stock_entry(领料) 返回异常: {str(r)[:300]}", False)
        raise SystemExit(1)
    mapped["custom_factory_order_no"] = "FO-2026-001"
    mapped.pop("name", None)
    for it in mapped.get("items", []):
        it.pop("name", None)
    se = new_doc("Stock Entry", mapped)
    STATE["se_mfg_transfer"] = se["name"]
    save_state()
    log(f"创建领料单 {se['name']}: "
        f"{[(c.get('item_code'), c.get('qty'), c.get('s_warehouse'), '->', c.get('t_warehouse')) for c in mapped.get('items', [])]}")
ensure_submitted("Stock Entry", STATE["se_mfg_transfer"], {"custom_factory_order_no": "FO-2026-001"})

# ============ 2. MES 工序报工（Job Card：成型工序 2000 双） ============
jc = get_doc("Job Card", JC)
if jc["docstatus"] == 0:
    if not jc.get("time_logs"):
        # 添加报工记录：员工 + 工时 + 完成数量
        jc.setdefault("time_logs", []).append({
            "doctype": "Job Card Time Log",
            "from_time": "2026-10-05 08:00:00",
            "to_time": "2026-10-05 18:00:00",
            "completed_qty": 2000,
        })
    else:
        for row in jc["time_logs"]:
            row["from_time"] = row.get("from_time") or "2026-10-05 08:00:00"
            row["to_time"] = row.get("to_time") or "2026-10-05 18:00:00"
            row["completed_qty"] = row.get("completed_qty") or 2000
    jc["custom_factory_order_no"] = "FO-2026-001"
    r = whitelisted("frappe.client.save", doc=jc)
    log(f"Job Card {JC} 已保存报工记录")
    d = ensure_submitted("Job Card", JC)
    wo = get_doc("Work Order", WO)
    log(f"工单状态: {wo.get('status')} | 工序完成数: "
        f"{[(o.get('operation'), o.get('completed_qty')) for o in wo.get('operations', [])]}")
else:
    log(f"Job Card {JC} 已提交 (status={jc.get('status')})")

# ============ 3. 完工入库：在制品仓 -> 成品仓 ============
if "se_manufacture" not in STATE:
    r = whitelisted("erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry",
                    work_order_id=WO, purpose="Manufacture")
    mapped = r.get("message")
    if not isinstance(mapped, dict) or mapped.get("doctype") != "Stock Entry":
        log(f"make_stock_entry(完工) 返回异常: {str(r)[:300]}", False)
        raise SystemExit(1)
    mapped["custom_factory_order_no"] = "FO-2026-001"
    mapped.pop("name", None)
    for it in mapped.get("items", []):
        it.pop("name", None)
    se = new_doc("Stock Entry", mapped)
    STATE["se_manufacture"] = se["name"]
    save_state()
    log(f"创建完工入库单 {se['name']}: 目标仓={mapped.get('to_warehouse')} "
        f"成品={[(c.get('item_code'), c.get('qty'), c.get('t_warehouse')) for c in mapped.get('items', [])]}")
ensure_submitted("Stock Entry", STATE["se_manufacture"], {"custom_factory_order_no": "FO-2026-001"})

# ============ 4. 验证 ============
wo = get_doc("Work Order", WO)
log(f"工单最终状态: {wo.get('status')} | 已生产: {wo.get('produced_qty')}")
log("=== 成品仓库存 ===")
for b in get_list("Bin", fields=["item_code", "warehouse", "actual_qty"],
                 filters=[["warehouse", "=", "成品仓 - 奥登科"]], limit=0):
    log(f"  {b['item_code']}: {b['actual_qty']}")

print("\n===== 流程3完成 =====")
print(json.dumps(STATE, ensure_ascii=False, indent=1))
