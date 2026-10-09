# -*- coding: utf-8 -*-
{
    "name": "奥登科·物料需求运算",
    "version": "20.0.1.0.0",
    "category": "Manufacturing/Inventory",
    "summary": "独立MRP物料需求运算：按BOM每双用量×订单数量自动算料，扣库存/在途/已订，欠料预警并一键转采购单",
    "description": """把旧系统 P11「物料需求计算」搬到 Odoo 20：
选款号 → 点「物料需求计算」→ 按量产 BOM 每双用量展开材料需求
→ 对比可用库存 / 在途 / 已订 → 得出采购欠量（标红）
→ 按损耗% / 采购比计算建议量 → 勾选欠料行一键转采购询价单。""",
    "author": "奥登科",
    "license": "LGPL-3",
    "depends": ["mrp", "purchase_stock"],
    "data": [
        "security/ir.access.csv",
        "data/sequence.xml",
        "views/mrp_calc_views.xml",
    ],
    "installable": True,
    "application": True,
}
