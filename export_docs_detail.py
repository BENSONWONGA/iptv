# -*- coding: utf-8 -*-
"""逐单拉取完整单据（含子表明细），补充迁移数据"""
import json
import requests

BASE = "http://220.162.99.166:88"
TOKEN = "77455c7d4b3a8fe:432939a748243fd"
s = requests.Session()
s.headers.update({"Authorization": f"token {TOKEN}", "Accept": "application/json"})

with open("/workspace/migration_data.json", encoding="utf-8") as f:
    out = json.load(f)

# 这些 doctype 需要拉完整单据（含子表）
FULL = ["Sales Order", "Purchase Order", "BOM", "Stock Entry", "Work Order", "Material Request"]

for dt in FULL:
    names = [r.get("name") for r in out.get(dt, [])]
    docs = []
    for n in names:
        try:
            r = s.get(f"{BASE}/api/resource/{dt}/{n}", timeout=30)
            if r.status_code == 200:
                docs.append(r.json().get("data", {}))
        except Exception as e:
            print(f"  {dt}/{n}: {e}")
    out[dt + " 完整单"] = docs
    print(f"{dt}: {len(docs)}/{len(names)} 完整单据")

# 库存现值：从 Stock Entry 明细重建（Material Transfer + Receipt + Issue）
quant = {}
for doc in out.get("Stock Entry 完整单", []):
    if doc.get("docstatus") != 1:
        continue
    kind = doc.get("purpose") or doc.get("stock_entry_type") or ""
    for it in doc.get("items", []):
        code = it.get("item_code")
        qty = it.get("qty") or 0
        basic = it.get("basic_qty") or qty
        s_wh = it.get("s_warehouse") or ""
        t_wh = it.get("t_warehouse") or ""
        if t_wh:  # 入库到 t_wh
            quant[(code, t_wh)] = quant.get((code, t_wh), 0) + basic
        if s_wh:  # 出库自 s_wh
            quant[(code, s_wh)] = quant.get((code, s_wh), 0) - basic

out["库存快照_重建"] = [
    {"item_code": k[0], "warehouse": k[1], "qty": round(v, 3)}
    for k, v in sorted(quant.items()) if abs(v) > 1e-6
]
print(f"库存快照: {len(out['库存快照_重建'])} 条（物料×仓库）")

with open("/workspace/migration_data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1, default=str)

print("完成 → /workspace/migration_data.json")
for k, v in out.items():
    if isinstance(v, list):
        print(f"  {k}: {len(v)}")
