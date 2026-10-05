# -*- coding: utf-8 -*-
"""流程4：委外加工费收货 -> 采购应付发票 -> 付款 -> 厂商对账"""
import json
import os
from api import get_doc, new_doc, submit_doc, get_list, whitelisted

COMPANY = "奥登科鞋业有限公司"
STATE_FILE = "/workspace/shoe_erp/state.json"
STATE = json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}


def save_state():
    json.dump(STATE, open(STATE_FILE, "w"), ensure_ascii=False, indent=1)


def log(msg, ok=True):
    print(("OK " if ok else "ERR") + " | " + msg)


# ============ 1. 委外收货单 -> 采购收货单（委外加工费） ============
if "pr_sub" not in STATE:
    r = whitelisted("erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt.make_purchase_receipt",
                    source_name=STATE["scr"], save=True, submit=True)
    doc = r.get("message") or {}
    if not doc.get("name"):
        log(f"委外加工费收货单创建失败: {str(r)[:300]}", False)
        raise SystemExit(1)
    STATE["pr_sub"] = doc["name"]
    save_state()
    log(f"委外加工费收货单 {doc['name']} 供应商={doc.get('supplier')} "
        f"docstatus={doc.get('docstatus')} 总额={doc.get('grand_total')}")
pr_sub = STATE["pr_sub"]
d = get_doc("Purchase Receipt", pr_sub)
log(f"委外加工费收货单 {pr_sub}: status={d.get('status')} 总额={d.get('grand_total')} "
    f"明细={[(i.get('item_code'), i.get('qty'), i.get('amount')) for i in d.get('items', [])]}")

# ============ 2. 生成采购应付发票（3张收货单 -> 3张发票） ============
CHILD_DOCTYPES = {
    "items": "Purchase Invoice Item",
    "taxes": "Purchase Taxes and Charges",
    "payment_schedule": "Payment Schedule",
}
for key, pr_name in [("pi1", STATE["pr_po1"]), ("pi2", STATE["pr_po2"]), ("pi_sub", pr_sub)]:
    if key in STATE:
        log(f"采购发票 {STATE[key]} 已存在")
        continue
    r = whitelisted("erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
                    source_name=pr_name)
    mapped = r.get("message")
    if not isinstance(mapped, dict) or not mapped.get("items"):
        log(f"make_purchase_invoice({pr_name}) 返回异常: {str(r)[:300]}", False)
        raise SystemExit(1)
    mapped["custom_factory_order_no"] = "FO-2026-001"
    mapped.pop("name", None)
    for tbl, child_dt in CHILD_DOCTYPES.items():
        for row in mapped.get(tbl) or []:
            row.pop("name", None)
            row.pop("parent", None)
            row["doctype"] = child_dt
    pi = new_doc("Purchase Invoice", mapped)
    STATE[key] = pi["name"]
    save_state()
    log(f"创建采购发票 {pi['name']} <- 收货 {pr_name} 供应商={pi.get('supplier')} 总额={pi.get('grand_total')}")
    if pi["docstatus"] == 0:
        submit_doc("Purchase Invoice", pi["name"])
        d2 = get_doc("Purchase Invoice", pi["name"])
        log(f"   已提交采购发票 {pi['name']} -> docstatus={d2['docstatus']} status={d2.get('status')}")

# ============ 3. 付款（Payment Entry，现金支付） ============
SUPPLIERS = {
    "pi1": "泉州兴发纺织有限公司",
    "pi2": "东莞宏力鞋材有限公司",
    "pi_sub": "莆田华盛针车厂",
}
PE_KEYS = {"pi1": "pe1", "pi2": "pe2", "pi_sub": "pe_sub"}
for pi_key, pe_key in PE_KEYS.items():
    if pe_key in STATE:
        log(f"付款单 {STATE[pe_key]} 已存在")
        continue
    pi = get_doc("Purchase Invoice", STATE[pi_key])
    amount = pi["base_grand_total"] or pi["grand_total"]
    pe = new_doc("Payment Entry", {
        "company": COMPANY,
        "payment_type": "Pay",
        "posting_date": "2026-10-05",
        "party_type": "Supplier",
        "party": SUPPLIERS[pi_key],
        "paid_from": "现金 - 奥登科",
        "paid_to": "债权人 - 奥登科",
        "mode_of_payment": "现金",
        "paid_amount": amount,
        "received_amount": amount,
        "source_exchange_rate": 1,
        "target_exchange_rate": 1,
        "references": [{
            "doctype": "Payment Entry Reference",
            "reference_doctype": "Purchase Invoice",
            "reference_name": pi["name"],
            "total_amount": amount,
            "allocated_amount": amount,
        }],
    })
    STATE[pe_key] = pe["name"]
    save_state()
    log(f"创建付款单 {pe['name']}: {SUPPLIERS[pi_key]} 金额={amount} 发票={pi['name']}")
    if pe["docstatus"] == 0:
        submit_doc("Payment Entry", pe["name"])
        log(f"   已提交付款单 {pe['name']}")

# ============ 4. 厂商对账（供应商应付余额与往来明细） ============
log("\n========== 厂商对账单 ==========")
for supplier in SUPPLIERS.values():
    log(f"\n--- {supplier} ---")
    total_invoiced = 0.0
    total_paid = 0.0
    # 应付发票
    pis = get_list("Purchase Invoice", fields=["name", "grand_total", "status"],
                   filters=[["supplier", "=", supplier], ["docstatus", "=", 1]], limit=0)
    for pi in pis:
        log(f"  发票 {pi['name']}: {pi['grand_total']} ({pi['status']})")
        total_invoiced += pi["grand_total"]
    # 付款记录
    pes = get_list("Payment Entry", fields=["name", "paid_amount", "status"],
                  filters=[["party", "=", supplier], ["party_type", "=", "Supplier"], ["docstatus", "=", 1]], limit=0)
    for pe in pes:
        log(f"  付款 {pe['name']}: {pe['paid_amount']} ({pe['status']})")
        total_paid += pe["paid_amount"]
    # 应付余额（债权人科目）
    gl = get_list("GL Entry", fields=["debit", "credit"],
                 filters=[["party", "=", supplier], ["account", "=", "债权人 - 奥登科"], ["is_cancelled", "=", 0]], limit=0)
    bal = sum(g["debit"] - g["credit"] for g in gl)
    log(f"  小计: 开票={total_invoiced}  已付={total_paid}  应付余额(GL)={bal}")

print("\n===== 流程4完成 =====")
print(json.dumps(STATE, ensure_ascii=False, indent=1))
