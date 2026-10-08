# -*- coding: utf-8 -*-
"""导出 ERPNext 全部业务数据为 JSON（迁移数据源 + 数据备份）"""
import json
import os
import time

import requests

B = "http://220.162.99.166:88"
T = "77455c7d4b3a8fe:432939a748243fd"
s = requests.Session()
s.headers.update({"Authorization": f"token {T}"})

# 全部需要迁移的业务数据（含主数据 + 交易 + 设置）
DOCTYPES = {
    "客户": "Customer", "供应商": "Supplier", "联系人": "Contact", "客户分组": "Customer Group",
    "供应商分组": "Supplier Group", "物料": "Item", "物料分组": "Item Group", "计量单位": "UOM",
    "价目表": "Price List", "物料价格": "Item Price", "BOM": "BOM", "仓库": "Warehouse",
    "销售订单": "Sales Order", "报价单": "Quotation", "销售出库单": "Delivery Note", "销售发票": "Sales Invoice",
    "采购申请": "Material Request", "采购订单": "Purchase Order", "采购收货单": "Purchase Receipt",
    "采购发票": "Purchase Invoice", "委外加工单": "Subcontracting Order", "委外收货单": "Subcontracting Receipt",
    "生产计划": "Production Plan", "生产工单": "Work Order", "工序报工": "Job Card",
    "库存出入库": "Stock Entry", "库存盘点": "Stock Reconciliation", "库存余额": "Bin",
    "收款单": "Payment Entry", "会计凭证": "Journal Entry", "会计科目": "Account", "成本中心": "Cost Center",
    "付款方式": "Mode of Payment", "公司": "Company", "项目": "Project", "员工": "Employee",
    "品质检验": "Quality Inspection", "工作站": "Workstation", "工序": "Operation",
}
OUT = "/workspace/erpnext_export"
os.makedirs(OUT, exist_ok=True)
summary = {}

for cn, dt in DOCTYPES.items():
    page, rows = 0, []
    t0 = time.time()
    while True:
        p = {"limit_page_length": 500, "limit_start": page * 500}
        j = s.get(f"{B}/api/resource/{dt}", params=p, timeout=120)
        if j.status_code != 200:
            print(f"跳过 {dt}: HTTP {j.status_code}")
            rows = None
            break
        data = j.json().get("data", [])
        rows.extend(data)
        if len(data) < 500:
            break
        page += 1
    if rows is None:
        summary[cn] = -1
        continue
    # 列表接口只给部分字段，重要单据补取完整字段
    summary[cn] = len(rows)
    with open(f"{OUT}/{dt.replace(' ', '_')}.json", "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False)
    print(f"{cn:<10} {dt:<24} {len(rows):>6} 条  {time.time()-t0:.1f}s")

with open(f"{OUT}/_summary.json", "w", encoding="utf-8") as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=1)
total = sum(v for v in summary.values() if v > 0)
print(f"\n导出完成: {total} 条业务记录 → {OUT}")
