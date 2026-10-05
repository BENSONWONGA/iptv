# -*- coding: utf-8 -*-
"""修复主数据：供应商分组/供应商/制造设置/SF-A001默认供应商 + 清理重复单据"""
from api import get_doc, get_list, new_doc, set_doc, submit_doc, cancel_doc, submit_doc as sb


def log(m, ok=True):
    print(("OK " if ok else "ERR") + " | " + m)


def exists(dt, name):
    try:
        get_doc(dt, name)
        return True
    except Exception:
        return False


def ensure(dt, name, payload):
    if exists(dt, name):
        log(f"{dt} 已存在: {name}")
        return
    try:
        new_doc(dt, payload)
        log(f"创建 {dt}: {name}")
    except Exception as e:
        log(f"创建 {dt} {name} 失败: {str(e)[:200]}", False)


# 1. 供应商分组
ensure("Supplier Group", "材料供应商", {"supplier_group_name": "材料供应商",
                                        "parent_supplier_group": "所有供应商组织", "is_group": 0})
ensure("Supplier Group", "委外加工厂", {"supplier_group_name": "委外加工厂",
                                       "parent_supplier_group": "所有供应商组织", "is_group": 0})

# 2. 供应商（并验证）
suppliers = [
    ("泉州兴发纺织有限公司", "材料供应商"),
    ("东莞宏力鞋材有限公司", "材料供应商"),
    ("莆田华盛针车厂", "委外加工厂"),
]
for name, group in suppliers:
    ensure("Supplier", name, {"supplier_name": name, "supplier_group": group, "country": "China"})

got = [s["name"] for s in get_list("Supplier", fields=["name"], limit=0)]
print("验证供应商列表:", got)
assert len(got) >= 3, "供应商创建失败！"

# 3. 制造设置（WIP 仓库必须）
try:
    set_doc("Manufacturing Settings", "Manufacturing Settings", {
        "default_wip_warehouse": "在制品 - 奥登科",
        "default_fg_warehouse": "成品仓 - 奥登科",
        "overproduction_percentage": 5.0,
    })
    ms = get_doc("Manufacturing Settings", "Manufacturing Settings")
    log(f"制造设置: WIP={ms.get('default_wip_warehouse')} FG={ms.get('default_fg_warehouse')}")
except Exception as e:
    log(f"制造设置失败: {str(e)[:200]}", False)

# 4. SF-A001 默认供应商（委外厂）
try:
    item = get_doc("Item", "SF-A001")
    defs = item.get("item_defaults") or []
    if defs:
        defs[0]["default_supplier"] = "莆田华盛针车厂"
        set_doc("Item", "SF-A001", {"item_defaults": defs})
    else:
        set_doc("Item", "SF-A001", {"item_defaults": [{
            "company": "奥登科鞋业有限公司",
            "default_warehouse": "半成品仓 - 奥登科",
            "default_supplier": "莆田华盛针车厂",
        }]})
    it = get_doc("Item", "SF-A001")
    log(f"SF-A001 默认供应商: {[(x.get('default_supplier')) for x in it.get('item_defaults')]}")
except Exception as e:
    log(f"SF-A001 供应商设置失败: {str(e)[:200]}", False)

# 5. 取消重复的销售订单 SAL-ORD-2026-00001
try:
    so1 = get_doc("Sales Order", "SAL-ORD-2026-00001")
    if so1["docstatus"] == 1:
        cancel_doc("Sales Order", "SAL-ORD-2026-00001")
        log("取消重复销售订单 SAL-ORD-2026-00001")
    else:
        log("SAL-ORD-2026-00001 状态:", so1["docstatus"])
except Exception as e:
    log(f"取消旧SO失败: {str(e)[:150]}", False)

# 6. 取消无供应商的生产计划 MFG-PP-2026-00002（会删除草稿工单）
try:
    pp2 = get_doc("Production Plan", "MFG-PP-2026-00002")
    if pp2["docstatus"] == 1:
        cancel_doc("Production Plan", "MFG-PP-2026-00002")
        log("取消生产计划 MFG-PP-2026-00002")
    wos = get_list("Work Order", fields=["name", "docstatus"], filters=[["production_plan", "=", "MFG-PP-2026-00002"]])
    log(f"残留工单: {wos}")
except Exception as e:
    log(f"取消PP失败: {str(e)[:150]}", False)
