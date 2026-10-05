# -*- coding: utf-8 -*-
"""勘察系统现状"""
import json
from api import get, get_list

out = {}

# 1. 已安装应用
try:
    apps = get("/api/method/frappe.apps.get_apps")
    out["apps"] = apps
except Exception as e:
    out["apps"] = str(e)

# 2. 公司
out["companies"] = get_list("Company", fields=["name", "abbr", "default_currency", "country", "is_group"])

# 3. 单位 UOM
out["uoms"] = get_list("UOM", fields=["uom_name", "enabled"])

# 4. 物料组
out["item_groups"] = get_list("Item Group", fields=["name", "parent_item_group", "is_group"])

# 5. 仓库
out["warehouses"] = get_list("Warehouse", fields=["name", "warehouse_type", "is_group", "parent_warehouse", "company"])

# 6. 物料属性
out["item_attributes"] = get_list("Item Attribute", fields=["attribute_name", "numeric_values"])

# 7. 物料（已有）
out["items"] = get_list("Item", fields=["item_code", "item_name", "item_group", "stock_uom", "is_stock_item"])

# 8. 供应商 / 客户
out["suppliers"] = get_list("Supplier", fields=["name", "supplier_group", "supplier_type"])
out["customers"] = get_list("Customer", fields=["name", "customer_group"])

# 9. 会计科目（费用类）
out["accounts"] = get_list("Account", fields=["name", "account_type", "root_type", "is_group"],
                            filters=[["account_type", "in", ["Stock", "Stock Received But Not Billed", "Expenses Included In Valuation"]]]) if False else get_list(
    "Account", fields=["name", "account_type", "is_group"], filters=[["is_group", "=", 0]], limit=50)

# 10. 员工/用户
out["territories"] = get_list("Territory", fields=["name", "is_group"], limit=10)

print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
