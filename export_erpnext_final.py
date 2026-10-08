# -*- coding: utf-8 -*-
"""从线上 ERPNext 导出业务数据（安装 Odoo 前抢救数据）"""
import json
import requests

BASE = "http://220.162.99.166:88"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"
s = requests.Session()
s.headers.update({"Authorization": f"token {TOKEN}", "Accept": "application/json"})

out = {}


def dump(doctype, fields=None, filters=None):
    """拉取 doctype 全量数据"""
    try:
        params = {"limit_page_length": 0}
        if fields:
            params["fields"] = json.dumps(fields)
        if filters:
            params["filters"] = json.dumps(filters)
        r = s.get(f"{BASE}/api/resource/{doctype}", params=params, timeout=60)
        if r.status_code != 200:
            print(f"  {doctype}: HTTP {r.status_code}（跳过）")
            return None
        data = r.json().get("data", [])
        print(f"  {doctype}: {len(data)} 条")
        return data
    except Exception as e:
        print(f"  {doctype}: 异常 {e}")
        return None


print("导出 ERPNext 业务数据：")
for dt in ["Customer", "Supplier", "Item", "Item Group", "BOM", "Sales Order",
           "Sales Order Item", "Purchase Order", "Stock Entry", "Stock Entry Detail",
           "Work Order", "Material Request", "Warehouse", "UOM"]:
    rows = dump(dt)
    if rows is not None:
        out[dt] = rows

# 库存快照（quant 层面）
try:
    r = s.get(f"{BASE}/api/method/frappe.client.get_list",
              params={"doctype": "Stock Ledger Entry", "limit_page_length": 0},
              timeout=60)
    print(f"  Stock Ledger Entry: HTTP {r.status_code}")
    if r.status_code == 200:
        out["Stock Ledger Entry"] = r.json().get("data", [])
        print(f"  库存流水: {len(out['Stock Ledger Entry'])} 条")
except Exception as e:
    print(f"  库存流水异常: {e}")

# 自定义单据类型兜底：指令单可能是自定义 DocType，扫一遍
try:
    r = s.get(f"{BASE}/api/resource/DocType",
              params={"limit_page_length": 0,
                      "filters": json.dumps([["module", "=", "Core"], ["custom", "=", 1]])},
              timeout=30)
    custom = r.json().get("data", []) if r.status_code == 200 else []
    print(f"  自定义 DocType: {len(custom)} 个")
    for d in custom:
        name = d.get("name")
        rows = dump(name)
        if rows:
            out[name] = rows
except Exception as e:
    print(f"  自定义 DocType 扫描异常: {e}")

with open("/workspace/migration_data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, default=str)

total = sum(len(v) if isinstance(v, list) else 0 for v in out.values())
print(f"\n合计 {total} 条记录 → /workspace/migration_data.json")
print("各类型:", {k: len(v) for k, v in out.items() if isinstance(v, list) and v})
