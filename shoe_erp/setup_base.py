# -*- coding: utf-8 -*-
"""阶段1：基础档案配置（币种/单位/物料组/仓库/属性/自定义字段）"""
import json
from api import get_doc, new_doc, set_doc, get_list, run_method

COMPANY = "奥登科鞋业有限公司"
results = []


def log(msg, ok=True):
    results.append(("OK " if ok else "ERR") + " | " + msg)
    print(("OK " if ok else "ERR") + " | " + msg)


def exists(doctype, name):
    try:
        get_doc(doctype, name)
        return True
    except Exception:
        return False


# ============ 1. 币种与时区修正 ============
try:
    if get_doc("Company", COMPANY).get("default_currency") != "CNY":
        set_doc("Company", COMPANY, {"default_currency": "CNY"})
        log("公司币种 ALL -> CNY")
    else:
        log("公司币种已是 CNY")
except Exception as e:
    log(f"公司币种修正失败: {str(e)[:200]}", False)

try:
    ss = get_doc("System Settings", "System Settings")
    upd = {}
    if ss.get("currency") != "CNY":
        upd["currency"] = "CNY"
    if ss.get("time_zone") != "Asia/Shanghai":
        upd["time_zone"] = "Asia/Shanghai"
    if ss.get("date_format") != "yyyy-mm-dd":
        upd["date_format"] = "yyyy-mm-dd"
    if upd:
        set_doc("System Settings", "System Settings", upd)
        log(f"系统设置修正: {upd}")
    else:
        log("系统设置已正确")
except Exception as e:
    log(f"系统设置修正失败: {str(e)[:200]}", False)

# ============ 2. 计量单位 ============
uoms = {
    "双": {"must_be_whole_number": 1},
    "码": {"must_be_whole_number": 1},
    "个": {"must_be_whole_number": 1},
}
for uom, props in uoms.items():
    try:
        if not exists("UOM", uom):
            new_doc("UOM", {"uom_name": uom, "enabled": 1, **props})
            log(f"创建单位: {uom}")
        else:
            log(f"单位已存在: {uom}")
    except Exception as e:
        log(f"单位 {uom} 失败: {str(e)[:200]}", False)

# ============ 3. 物料组 ============
groups = {
    "面料": "原材料",
    "里料": "原材料",
    "辅料": "原材料",
    "底材": "原材料",
    "成品鞋": "产品展示",
    "委外加工服务": "服务",
}
for g, parent in groups.items():
    try:
        if not exists("Item Group", g):
            new_doc("Item Group", {"item_group_name": g, "parent_item_group": parent, "is_group": 0})
            log(f"创建物料组: {g}")
        else:
            log(f"物料组已存在: {g}")
    except Exception as e:
        log(f"物料组 {g} 失败: {str(e)[:200]}", False)

# ============ 4. 仓库 ============
warehouses = ["材料仓", "半成品仓", "成品仓", "委外供应商仓"]
for w in warehouses:
    name = f"{w} - 奥登科"
    try:
        if not exists("Warehouse", name):
            new_doc("Warehouse", {
                "warehouse_name": w,
                "parent_warehouse": "所有仓库 - 奥登科",
                "company": COMPANY,
                "warehouse_type": "",
            })
            log(f"创建仓库: {name}")
        else:
            log(f"仓库已存在: {name}")
    except Exception as e:
        log(f"仓库 {name} 失败: {str(e)[:200]}", False)

# ============ 5. 物料属性值（尺码/颜色） ============
# 尺寸属性: 添加 35-45
try:
    attr = get_doc("Item Attribute", "尺寸")
    existing_vals = [r.get("attribute_value") for r in attr.get("item_attribute_values", [])]
    new_vals = []
    for size in range(35, 46):
        if str(size) not in existing_vals:
            new_vals.append({"attribute_value": str(size), "abbr": str(size)})
    if new_vals:
        attr.setdefault("item_attribute_values", []).extend(new_vals)
        set_doc("Item Attribute", "尺寸", {"item_attribute_values": attr["item_attribute_values"]})
        log(f"尺寸属性添加 {len(new_vals)} 个尺码值")
    else:
        log("尺寸属性值已齐全")
except Exception as e:
    log(f"尺寸属性失败: {str(e)[:300]}", False)

# 颜色属性
try:
    attr = get_doc("Item Attribute", "颜色")
    existing_vals = [r.get("attribute_value") for r in attr.get("item_attribute_values", [])]
    colors = [("黑色", "BK"), ("白色", "WH"), ("藏青", "NV"), ("灰色", "GY"), ("红色", "RD")]
    new_vals = [{"attribute_value": c, "abbr": a} for c, a in colors if c not in existing_vals]
    if new_vals:
        attr.setdefault("item_attribute_values", []).extend(new_vals)
        set_doc("Item Attribute", "颜色", {"item_attribute_values": attr["item_attribute_values"]})
        log(f"颜色属性添加 {len(new_vals)} 个颜色值")
    else:
        log("颜色属性值已齐全")
except Exception as e:
        log(f"颜色属性失败: {str(e)[:300]}", False)

# ============ 6. 自定义字段 ============
custom_fields = [
    # 物料 - 款号
    {"dt": "Item", "fieldname": "custom_style_no", "label": "款号", "fieldtype": "Data",
     "insert_after": "item_group", "in_standard_filter": 1, "search_index": 1, "no_copy": 1},
    # 销售订单 - 工厂指令单号 + 款号
    {"dt": "Sales Order", "fieldname": "custom_factory_order_no", "label": "工厂指令单号",
     "fieldtype": "Data", "insert_after": "po_no", "in_standard_filter": 1, "no_copy": 1, "allow_in_quick_entry": 1},
    {"dt": "Sales Order", "fieldname": "custom_style_no", "label": "款号", "fieldtype": "Data",
     "insert_after": "custom_factory_order_no", "no_copy": 1},
    # 工单
    {"dt": "Work Order", "fieldname": "custom_factory_order_no", "label": "工厂指令单号",
     "fieldtype": "Data", "insert_after": "bom_no", "in_standard_filter": 1, "no_copy": 1},
    {"dt": "Work Order", "fieldname": "custom_style_no", "label": "款号", "fieldtype": "Data",
     "insert_after": "custom_factory_order_no", "no_copy": 1},
    # 采购订单
    {"dt": "Purchase Order", "fieldname": "custom_factory_order_no", "label": "工厂指令单号",
     "fieldtype": "Data", "insert_after": "transaction_date", "in_standard_filter": 1, "no_copy": 1},
    # 库存录入单（扫描出入库）
    {"dt": "Stock Entry", "fieldname": "custom_factory_order_no", "label": "工厂指令单号",
     "fieldtype": "Data", "insert_after": "stock_entry_type", "in_standard_filter": 1, "no_copy": 1},
    # 委外订单
    {"dt": "Subcontracting Order", "fieldname": "custom_factory_order_no", "label": "工厂指令单号",
     "fieldtype": "Data", "insert_after": "transaction_date", "in_standard_filter": 1, "no_copy": 1},
    # 工作票 MES
    {"dt": "Job Card", "fieldname": "custom_factory_order_no", "label": "工厂指令单号",
     "fieldtype": "Data", "insert_after": "operation", "in_standard_filter": 1, "no_copy": 1},
]

for cf in custom_fields:
    dt, fn = cf["dt"], cf["fieldname"]
    try:
        existing = get_list("Custom Field", fields=["name"], filters=[["dt", "=", dt], ["fieldname", "=", fn]])
        if existing:
            log(f"自定义字段已存在: {dt}.{fn}")
            continue
        new_doc("Custom Field", cf)
        log(f"创建自定义字段: {dt}.{fn} ({cf['label']})")
    except Exception as e:
        log(f"自定义字段 {dt}.{fn} 失败: {str(e)[:200]}", False)

# 清理缓存让自定义字段生效
try:
    run_method("frappe.client.clear_cache")
    log("清理缓存")
except Exception:
    try:
        for cf in custom_fields:
            run_method("frappe.client.clear_cache", doctype=cf["dt"])
        log("清理缓存(逐个)")
    except Exception as e:
        log(f"清缓存失败(可忽略): {str(e)[:150]}", False)

# ============ 7. 供应商分组 ============
for sg in ["材料供应商", "委外加工厂"]:
    try:
        if not exists("Supplier Group", sg):
            new_doc("Supplier Group", {"supplier_group_name": sg, "parent_supplier_group": "All Supplier Groups", "is_group": 0})
            log(f"创建供应商分组: {sg}")
        else:
            log(f"供应商分组已存在: {sg}")
    except Exception as e:
        log(f"供应商分组 {sg} 失败: {str(e)[:150]}", False)

print("\n========== 阶段1 完成 ==========")
errs = [r for r in results if r.startswith("ERR")]
print(f"总计 {len(results)} 项, 失败 {len(errs)} 项")
for e in errs:
    print(e)
