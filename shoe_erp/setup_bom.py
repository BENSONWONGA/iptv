# -*- coding: utf-8 -*-
"""阶段3：BOM 建立（半成品帮面 BOM + 成品 BOM + 委外加工 BOM）"""
import json
from api import get_doc, new_doc, set_doc, submit_doc, get_list

COMPANY = "奥登科鞋业有限公司"
results = []


def log(msg, ok=True):
    results.append(("OK " if ok else "ERR") + " | " + msg)
    print(("OK " if ok else "ERR") + " | " + msg)


def find_bom(item):
    rows = get_list("BOM", fields=["name", "docstatus", "is_default"],
                    filters=[["item", "=", item], ["is_active", "=", 1]])
    return rows


def create_bom(item, qty, materials, operations, note):
    try:
        existing = find_bom(item)
        if existing:
            log(f"{item} 已有 BOM: {existing}")
            b = existing[0]
            if b["docstatus"] == 0:
                submit_doc("BOM", b["name"])
                log(f"提交 BOM {b['name']}")
            return b["name"]
        bom = new_doc("BOM", {
            "item": item,
            "quantity": qty,
            "uom": "双",
            "is_active": 1,
            "is_default": 1,
            "with_operations": 1 if operations else 0,
            "items": [{"item_code": m[0], "qty": m[1]} for m in materials],
            "operations": [{"operation": o[0], "workstation": o[1], "time_in_mins": o[2]} for o in operations],
        })
        if "data" not in bom:
            raise Exception(str(bom)[:300])
        name = bom["data"]["name"]
        submit_doc("BOM", name)
        log(f"创建并提交 {item} BOM: {name} ({note})")
        return name
    except Exception as e:
        log(f"{item} BOM 失败: {str(e)[:300]}", False)
        return None


# ============ 1. 半成品帮面 BOM ============
bom_sf = create_bom(
    item="SF-A001",
    qty=1,
    materials=[
        ("M-FAB-001", 0.5),    # 牛巴戈面料 0.5码/双
        ("M-LIN-001", 0.35),   # 针织里布 0.35码/双
        ("M-ACC-001", 12),     # 鞋眼扣 12个/双
        ("M-ACC-002", 0.02),   # 缝纫线 0.02卷/双
    ],
    operations=[
        ("裁断", "裁断车间", 3),
        ("针车", "针车线-委外", 15),
    ],
    note="裁断+针车（针车委外）",
)

# ============ 2. 成品 BOM（41码黑色变体） ============
bom_fg = create_bom(
    item="FG-A001-41-BK",
    qty=1,
    materials=[
        ("SF-A001", 1),        # 帮面 1双/双
        ("M-BOT-001", 1),      # 橡胶大底 1双/双
        ("M-BOT-002", 1),      # EVA中底 1双/双
        ("M-CHE-001", 0.01),   # 热熔胶 0.01包/双
    ],
    operations=[
        ("成型", "成型车间A线", 10),
    ],
    note="成型工序（厂内）",
)

# ============ 3. 设置 Item 默认 BOM ============
for item, bom in [("SF-A001", bom_sf), ("FG-A001-41-BK", bom_fg)]:
    if bom:
        try:
            set_doc("Item", item, {"default_bom": bom})
            log(f"设置 {item} 默认BOM: {bom}")
        except Exception as e:
            log(f"设置 {item} default_bom 失败: {str(e)[:200]}", False)

# ============ 4. 委外加工 BOM（Subcontracting BOM） ============
if bom_sf:
    try:
        existing = get_list("Subcontracting BOM", fields=["name"],
                            filters=[["finished_good", "=", "SF-A001"]])
        if existing:
            log(f"委外BOM已存在: {existing[0]['name']}")
        else:
            r = new_doc("Subcontracting BOM", {
                "is_active": 1,
                "finished_good": "SF-A001",
                "finished_good_qty": 1,
                "finished_good_bom": bom_sf,
                "service_item": "SVC-STI",
                "service_item_qty": 1,
                "service_item_uom": "双",
                "finished_good_uom": "双",
                "conversion_factor": 1,
            })
            if "data" in r:
                log(f"创建委外BOM: {r['data']['name']} (帮面针车 -> SVC-STI)")
            else:
                log(f"委外BOM失败: {str(r)[:300]}", False)
    except Exception as e:
        log(f"委外BOM失败: {str(e)[:300]}", False)

print("\n========== 阶段3 完成 ==========")
errs = [r for r in results if r.startswith("ERR")]
print(f"总计 {len(results)} 项, 失败 {len(errs)} 项")
for e in errs:
    print(e)
