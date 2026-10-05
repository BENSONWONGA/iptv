# -*- coding: utf-8 -*-
"""补全 MRP 字段修复：回填 Material Request 的 custom_factory_order_no
上轮已创建 Custom Field，但 MAT-MR-2026-00001（已提交）的值未回填，导致 UI 链路 MRP 断链。
"""
import json
from api import get_doc, set_doc, get_list, whitelisted

CF = "Material Request-custom_factory_order_no"
MR = "MAT-MR-2026-00001"
FO = "FO-2026-001"

mr = get_doc("Material Request", MR)
print("[1] 当前值:", repr(mr.get("custom_factory_order_no")), "docstatus:", mr.get("docstatus"))

if mr.get("custom_factory_order_no") != FO:
    cf = get_doc("Custom Field", CF)
    if not cf.get("allow_on_submit"):
        set_doc("Custom Field", CF, {"allow_on_submit": 1})
        print("[2] Custom Field allow_on_submit -> 1")
    else:
        print("[2] allow_on_submit 已开启")
    r = whitelisted("frappe.client.set_value",
                    doctype="Material Request", name=MR,
                    fieldname="custom_factory_order_no", value=FO)
    print("[3] set_value 返回:", json.dumps(r.get("message"), ensure_ascii=False))
else:
    print("[skip] 值已正确")

mr2 = get_doc("Material Request", MR)
print("[4] 回填后值:", repr(mr2.get("custom_factory_order_no")))
got = get_list("Material Request", fields=["name", "docstatus", "status"],
               filters=[["custom_factory_order_no", "=", FO]])
print("[5] 按 FO 过滤 MR ->", json.dumps(got, ensure_ascii=False))
assert any(x["name"] == MR for x in got), "回填失败！"
print("[DONE] MRP 链路数据修复完成")
