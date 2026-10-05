# -*- coding: utf-8 -*-
"""阶段2：主数据（物料/供应商/客户/工序/工作中心）"""
import json
from api import get_doc, new_doc, get_list

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


def ensure(doctype, name, payload):
    if exists(doctype, name):
        log(f"{doctype} 已存在: {name}")
        return get_doc(doctype, name)
    try:
        r = new_doc(doctype, payload)
        if "data" in r:
            log(f"创建 {doctype}: {name}")
            return r["data"]
        raise Exception(str(r)[:300])
    except Exception as e:
        log(f"创建 {doctype} {name} 失败: {str(e)[:300]}", False)
        return None


# ============ 1. 材料 + 半成品 + 服务物料 ============
items = [
    # code, 名称, 物料组, 单位, 默认仓库, 采购价(参考), 条码, 描述
    ("M-FAB-001", "牛巴戈面料(黑色)", "面料", "码", "材料仓 - 奥登科", 25, "6901234500011", "鞋面用牛巴戈二层革 1.4mm"),
    ("M-LIN-001", "针织里布", "里料", "码", "材料仓 - 奥登科", 8, "6901234500028", "涤纶针织网布里布"),
    ("M-ACC-001", "鞋眼扣", "辅料", "个", "材料仓 - 奥登科", 0.3, "6901234500035", "五金鞋眼扣 镍色"),
    ("M-ACC-002", "涤纶缝纫线", "辅料", "个", "材料仓 - 奥登科", 2.0, "6901234500042", "602涤纶缝纫线 5000m/卷"),
    ("M-BOT-001", "橡胶大底", "底材", "双", "材料仓 - 奥登科", 18, "6901234500059", "模压橡胶大底 MD-41"),
    ("M-BOT-002", "EVA中底", "底材", "双", "材料仓 - 奥登科", 6, "6901234500066", "二次发泡EVA中底"),
    ("M-CHE-001", "热熔胶", "辅料", "个", "材料仓 - 奥登科", 15, "6901234500073", "片状热熔胶 1kg/包"),
]

for code, name, group, uom, wh, rate, barcode, desc in items:
    payload = {
        "item_code": code,
        "item_name": name,
        "item_group": group,
        "stock_uom": uom,
        "is_stock_item": 1,
        "is_purchase_item": 1,
        "is_sales_item": 0,
        "description": desc,
        "standard_rate": rate,
        "item_defaults": [{"company": COMPANY, "default_warehouse": wh}],
        "barcodes": [{"barcode": barcode}],
    }
    ensure("Item", code, payload)

# 半成品：帮面（委外针车加工回来）
ensure("Item", "SF-A001", {
    "item_code": "SF-A001",
    "item_name": "帮面-黑色(针车半成品)",
    "item_group": "半成品",
    "stock_uom": "双",
    "is_stock_item": 1,
    "is_purchase_item": 0,
    "is_sales_item": 0,
    "is_sub_contracted_item": 1,
    "description": "STYLE-A001 帮面半成品（裁断+针车后）",
    "item_defaults": [{"company": COMPANY, "default_warehouse": "半成品仓 - 奥登科"}],
    "barcodes": [{"barcode": "6901234510002"}],
})

# 委外加工服务物料：针车加工费
ensure("Item", "SVC-STI", {
    "item_code": "SVC-STI",
    "item_name": "针车加工费",
    "item_group": "委外加工服务",
    "stock_uom": "双",
    "is_stock_item": 0,
    "is_purchase_item": 1,
    "is_sales_item": 0,
    "is_service_item": 1,
    "include_item_in_manufacturing": 1,
    "standard_rate": 12,
    "description": "帮面针车工序委外加工费（按双计）",
})

# ============ 2. 成品（模板+变体） ============
ensure("Item", "FG-A001", {
    "item_code": "FG-A001",
    "item_name": "男士运动鞋 STYLE-A001",
    "item_group": "成品鞋",
    "stock_uom": "双",
    "is_stock_item": 1,
    "has_variants": 1,
    "is_sales_item": 1,
    "is_purchase_item": 0,
    "custom_style_no": "A001",
    "description": "STYLE-A001 男士休闲运动鞋（按尺码/颜色变体）",
    "attributes": [
        {"attribute": "尺寸"},
        {"attribute": "颜色"},
    ],
    "item_defaults": [{"company": COMPANY, "default_warehouse": "成品仓 - 奥登科"}],
})

# 变体：40/41/42/43 黑色
variants = [
    ("FG-A001-40-BK", "40", "黑色"),
    ("FG-A001-41-BK", "41", "黑色"),
    ("FG-A001-42-BK", "42", "黑色"),
    ("FG-A001-43-BK", "43", "黑色"),
]
barcodes_v = {"FG-A001-40-BK": "6901234520401", "FG-A001-41-BK": "6901234520418",
              "FG-A001-42-BK": "6901234520425", "FG-A001-43-BK": "6901234520432"}
for code, size, color in variants:
    ensure("Item", code, {
        "item_code": code,
        "item_name": f"男士运动鞋 STYLE-A001 {size}码{color}",
        "item_group": "成品鞋",
        "stock_uom": "双",
        "is_stock_item": 1,
        "is_sales_item": 1,
        "is_purchase_item": 0,
        "variant_of": "FG-A001",
        "custom_style_no": "A001",
        "description": f"STYLE-A001 {size}码 {color}",
        "attributes": [
            {"attribute": "尺寸", "attribute_value": size},
            {"attribute": "颜色", "attribute_value": color},
        ],
        "standard_rate": 120,
        "item_defaults": [{"company": COMPANY, "default_warehouse": "成品仓 - 奥登科"}],
        "barcodes": [{"barcode": barcodes_v[code]}],
    })

# ============ 3. 供应商 ============
suppliers = [
    ("泉州兴发纺织有限公司", "材料供应商", "SUP-001"),
    ("东莞宏力鞋材有限公司", "材料供应商", "SUP-002"),
    ("莆田华盛针车厂", "委外加工厂", "SUP-003"),
]
for name, group, code in suppliers:
    if not exists("Supplier", name):
        try:
            new_doc("Supplier", {
                "supplier_name": name,
                "supplier_group": group,
                "country": "China",
                "supplier_code": code,
            })
            log(f"创建供应商: {name}")
        except Exception as e:
            log(f"供应商 {name} 失败: {str(e)[:200]}", False)
    else:
        log(f"供应商已存在: {name}")

# ============ 4. 客户 ============
ensure("Customer Group", "外贸客户", {
    "customer_group_name": "外贸客户", "parent_customer_group": "All Customer Groups", "is_group": 0,
})
ensure("Customer", "美星国际贸易有限公司", {
    "customer_name": "美星国际贸易有限公司",
    "customer_type": "Company",
    "customer_group": "外贸客户",
    "territory": "世界其他地区",
})

# ============ 5. 工作中心（车间） ============
workstations = [
    ("裁断车间", "裁断机台 × 6，冲裁面料/里料", 200),
    ("针车线-委外", "委外针车加工线（莆田华盛）", 500),
    ("成型车间A线", "双密度注塑成型线", 800),
]
for name, desc, capacity in workstations:
    if not exists("Workstation", name):
        try:
            new_doc("Workstation", {
                "workstation_name": name,
                "description": desc,
                "production_capacity": capacity,
            })
            log(f"创建工作中心: {name}")
        except Exception as e:
            log(f"工作中心 {name} 失败: {str(e)[:200]}", False)
    else:
        log(f"工作中心已存在: {name}")

# ============ 6. 工序 ============
operations = [
    ("裁断", "裁断车间", "面料/里料冲裁裁断", 3),
    ("针车", "针车线-委外", "帮面缝合针车工序（委外）", 15),
    ("成型", "成型车间A线", "拉帮成型/压底/冷冻定型", 10),
]
for name, ws, desc, mins in operations:
    if not exists("Operation", name):
        try:
            new_doc("Operation", {
                "name": name,
                "workstation": ws,
                "description": desc,
                "batch_size": 0,
            })
            log(f"创建工序: {name}")
        except Exception as e:
            log(f"工序 {name} 失败: {str(e)[:200]}", False)
    else:
        log(f"工序已存在: {name}")

print("\n========== 阶段2 完成 ==========")
errs = [r for r in results if r.startswith("ERR")]
print(f"总计 {len(results)} 项, 失败 {len(errs)} 项")
for e in errs:
    print(e)
